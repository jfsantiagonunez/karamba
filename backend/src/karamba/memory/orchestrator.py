"""LangGraph orchestrator for conversation management with multi-agent routing."""
from typing import TypedDict, Annotated, Optional, AsyncIterator, Union
from operator import add
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from karamba.core.agent import KarambaAgent
from karamba.core.models import AgentRequest, PhaseResult
from karamba.agents.router import AgentRouter
from .models import SessionState, MessageRole
from .store import SessionStore


class GraphState(TypedDict):
    """State for the conversation graph."""
    session_id: str
    query: str
    conversation_history: list[dict]
    phase_results: Annotated[list[dict], add]
    answer: str
    citations: list[dict]
    document_ids: list[str]

    # Agent routing state
    selected_agent_id: str
    routing_confidence: float
    routing_reasoning: str

    # Human-in-the-loop state
    requires_approval: bool
    pending_action: Optional[dict]
    approved: bool

    # Reflection state (for future use)
    reflection_count: int
    quality_score: Optional[float]


class ConversationOrchestrator:
    """Orchestrates conversation flow with memory, multi-agent routing, and HITL support."""

    def __init__(
        self,
        agent: Union[KarambaAgent, AgentRouter],
        session_store: SessionStore,
        enable_reflection: bool = False,
        max_reflection_iterations: int = 2
    ):
        """
        Initialize orchestrator with agent or router.

        Args:
            agent: Either a single KarambaAgent (legacy) or an AgentRouter (multi-agent)
            session_store: Session storage for conversation memory
            enable_reflection: Whether to enable reflection pattern
            max_reflection_iterations: Maximum number of reflection iterations
        """
        self.agent = agent
        self.use_router = isinstance(agent, AgentRouter)
        self.session_store = session_store
        self.enable_reflection = enable_reflection
        self.max_reflection_iterations = max_reflection_iterations
        self._graph = None  # Lazy initialization

        mode = "multi-agent" if self.use_router else "single-agent"
        logger.info(f"Conversation orchestrator initialized in {mode} mode")

    @property
    def graph(self):
        """Lazy graph initialization."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("process_query", self._process_query_node)

        # Add routing node if using multi-agent router
        if self.use_router:
            workflow.add_node("route_query", self._route_query_node)

        workflow.add_node("check_approval", self._check_approval_node)
        workflow.add_node("execute_agent", self._execute_agent_node)

        if self.enable_reflection:
            workflow.add_node("reflect", self._reflect_node)

        # Define edges
        workflow.set_entry_point("process_query")

        if self.use_router:
            workflow.add_edge("process_query", "route_query")
            workflow.add_edge("route_query", "check_approval")
        else:
            workflow.add_edge("process_query", "check_approval")

        # Conditional edge for approval
        workflow.add_conditional_edges(
            "check_approval",
            self._should_wait_for_approval,
            {
                "approved": "execute_agent",
                "waiting": END,  # Interrupt for human approval
                "skip": "execute_agent"
            }
        )

        if self.enable_reflection:
            # Conditional edge for reflection
            workflow.add_conditional_edges(
                "execute_agent",
                self._should_reflect,
                {
                    "reflect": "reflect",
                    "done": END
                }
            )
            workflow.add_conditional_edges(
                "reflect",
                self._should_continue_reflection,
                {
                    "continue": "execute_agent",
                    "done": END
                }
            )
        else:
            workflow.add_edge("execute_agent", END)

        return workflow.compile(
            checkpointer=self.session_store.checkpointer,  # None if not initialized yet
            interrupt_before=["check_approval"] if False else None  # Disable HITL for now - queries were getting stuck
        )

    async def _process_query_node(self, state: GraphState) -> GraphState:
        """Process incoming query and load conversation history."""
        logger.info(f"Processing query for session: {state['session_id']}")

        # Load conversation history
        history = await self.session_store.get_conversation_history(
            state["session_id"],
            limit=10  # Last 10 messages for context
        )

        if history:
            state["conversation_history"] = [
                {"role": msg.role.value, "content": msg.content}
                for msg in history.messages
            ]

        # Add current query to conversation
        await self.session_store.add_message(
            state["session_id"],
            MessageRole.USER,
            state["query"]
        )

        return state

    async def _route_query_node(self, state: GraphState) -> GraphState:
        """Route query to appropriate specialist agent (multi-agent mode)."""
        logger.info(f"Routing query for session: {state['session_id']}")

        # Build routing context
        context = {
            "conversation_history": state.get("conversation_history", []),
            "session_id": state["session_id"]
        }

        # Use router to select best agent
        decision = await self.agent.route(state["query"], context)

        state["selected_agent_id"] = decision.agent_id
        state["routing_confidence"] = decision.confidence
        state["routing_reasoning"] = decision.reasoning

        logger.info(
            f"Routed to agent: {decision.agent_id} "
            f"(confidence: {decision.confidence:.2f})"
        )

        return state

    async def _check_approval_node(self, state: GraphState) -> GraphState:
        """Check if query requires approval (HITL) based on agent metadata and context."""
        logger.info(f"=== CHECK_APPROVAL_NODE CALLED for session: {state['session_id']} ===")

        requires_approval = False
        approval_reason = None

        # Check if we're using multi-agent routing
        if self.use_router:
            agent_id = state.get("selected_agent_id")
            if agent_id:
                selected_agent = self.agent.registry.get(agent_id)
                if selected_agent:
                    # Use agent's approval policy
                    requires_approval, approval_reason = selected_agent.requires_approval(
                        query=state["query"],
                        detected_actions=None,  # Phase results not available yet
                        context={"session_id": state["session_id"]}
                    )
                    logger.info(
                        f"Agent {agent_id} approval check: "
                        f"requires={requires_approval}, reason={approval_reason}"
                    )

        # Fallback to simple keyword-based check if no agent-specific policy
        if not requires_approval and not self.use_router:
            query_lower = state["query"].lower()
            risky_keywords = ["delete", "remove", "clear all"]
            for keyword in risky_keywords:
                if keyword in query_lower:
                    requires_approval = True
                    approval_reason = f"Query contains potentially destructive keyword: '{keyword}'"
                    break

        state["requires_approval"] = requires_approval
        logger.info(f"Requires approval: {requires_approval}, approved: {state.get('approved', False)}")

        if requires_approval and not state.get("approved", False):
            # Request approval
            action = {
                "action_id": f"action_{state['session_id']}",
                "action_type": "query_execution",
                "query": state["query"],
                "reason": approval_reason or "Query requires approval"
            }
            await self.session_store.request_approval(state["session_id"], action)
            state["pending_action"] = action
            logger.info(f"Approval required for session: {state['session_id']}, reason: {approval_reason}")

        return state

    def _should_wait_for_approval(self, state: GraphState) -> str:
        """Determine if we should wait for approval."""
        if not state.get("requires_approval", False):
            return "skip"

        if state.get("approved", False):
            return "approved"

        return "waiting"

    async def _execute_agent_node(self, state: GraphState) -> GraphState:
        """Execute the selected agent with its phase engine."""
        logger.info(f"=== EXECUTE_AGENT_NODE CALLED for session: {state['session_id']} ===")

        # Create agent request with conversation context
        agent_request = AgentRequest(
            query=state["query"],
            session_id=state["session_id"],
            document_ids=state.get("document_ids", []),
            config={
                "conversation_history": state.get("conversation_history", [])
            }
        )
        logger.info(f"Created AgentRequest with {len(state.get('document_ids', []))} documents")

        # Get the appropriate agent
        if self.use_router:
            # Multi-agent mode: get the selected agent
            agent_id = state.get("selected_agent_id")
            logger.info(f"Looking for agent: {agent_id}")
            selected_agent = self.agent.registry.get(agent_id)

            if not selected_agent:
                logger.error(f"Agent not found: {agent_id}")
                raise ValueError(f"Agent not found: {agent_id}")

            logger.info(f"Using specialist agent: {selected_agent.metadata.name}")

            # Execute through specialist agent
            logger.info(f"About to call process_query on {agent_id}")
            response = await selected_agent.process_query(
                agent_request,
                session_context={"conversation_history": state.get("conversation_history", [])}
            )
            logger.info(f"process_query returned, answer length: {len(response.answer) if response.answer else 0}")
        else:
            # Single agent mode (legacy)
            response = await self.agent.answer_question(agent_request)

        # Update state with results
        state["answer"] = response.answer
        state["citations"] = response.citations
        state["phase_results"] = [
            result.model_dump() for result in response.phase_results
        ]

        # Prepare metadata for conversation storage
        metadata = {
            "citations": response.citations
        }

        if self.use_router:
            metadata["agent_id"] = state.get("selected_agent_id")
            metadata["agent_name"] = selected_agent.metadata.name
            metadata["routing_confidence"] = state.get("routing_confidence")
            metadata["routing_reasoning"] = state.get("routing_reasoning")

        # Add assistant response to conversation
        await self.session_store.add_message(
            state["session_id"],
            MessageRole.ASSISTANT,
            response.answer,
            metadata=metadata
        )

        logger.info(f"Agent execution complete for session: {state['session_id']}")
        return state

    async def _reflect_node(self, state: GraphState) -> GraphState:
        """Reflection node for self-critique (future enhancement)."""
        logger.info(f"Reflecting on response for session: {state['session_id']}")

        # TODO: Implement reflection logic
        # - Evaluate answer quality
        # - Check for factual accuracy
        # - Identify gaps in reasoning

        state["reflection_count"] = state.get("reflection_count", 0) + 1
        state["quality_score"] = 0.85  # Placeholder

        return state

    def _should_reflect(self, state: GraphState) -> str:
        """Determine if reflection is needed."""
        if not self.enable_reflection:
            return "done"

        # Check if we should reflect
        quality_score = state.get("quality_score", 1.0)
        reflection_count = state.get("reflection_count", 0)

        if quality_score < 0.7 and reflection_count < self.max_reflection_iterations:
            return "reflect"

        return "done"

    def _should_continue_reflection(self, state: GraphState) -> str:
        """Determine if we should continue reflection loop."""
        quality_score = state.get("quality_score", 1.0)
        reflection_count = state.get("reflection_count", 0)

        if quality_score < 0.8 and reflection_count < self.max_reflection_iterations:
            return "continue"

        return "done"

    async def query(
        self,
        session_id: str,
        query: str,
        document_ids: list[str] = None,
        approved: bool = False
    ) -> dict:
        """Execute a query through the orchestrated workflow."""
        # Ensure session exists
        session_state = await self.session_store.get_session(session_id)
        if not session_state:
            session_state = await self.session_store.create_session(session_id)

        # Use session's documents if not explicitly provided
        # This links documents to the chat session
        if document_ids is None:
            document_ids = session_state.document_ids

        logger.info(
            f"Query for session {session_id} using {len(document_ids)} documents: {document_ids}"
        )

        # Create initial graph state
        initial_state: GraphState = {
            "session_id": session_id,
            "query": query,
            "conversation_history": [],
            "phase_results": [],
            "answer": "",
            "citations": [],
            "document_ids": document_ids,
            "selected_agent_id": "",
            "routing_confidence": 0.0,
            "routing_reasoning": "",
            "requires_approval": False,
            "pending_action": None,
            "approved": approved,
            "reflection_count": 0,
            "quality_score": None
        }

        # Execute graph
        config = {"configurable": {"thread_id": session_state.thread_id}}
        result = await self.graph.ainvoke(initial_state, config)

        return result

    async def stream_query(
        self,
        session_id: str,
        query: str,
        document_ids: list[str] = None,
        approved: bool = False
    ):
        """
        Stream query execution with real-time phase updates.

        Yields dictionaries with phase updates and final result.
        """
        # Ensure session exists
        session_state = await self.session_store.get_session(session_id)
        if not session_state:
            session_state = await self.session_store.create_session(session_id)

        # Use session's documents if not explicitly provided
        if document_ids is None:
            document_ids = session_state.document_ids

        logger.info(
            f"Streaming query for session {session_id} using {len(document_ids)} documents"
        )

        # Add user message to conversation
        await self.session_store.add_message(
            session_id,
            MessageRole.USER,
            query
        )

        # Initialize variables
        decision = None
        selected_agent = None

        # Yield initial routing event
        yield {
            "type": "routing",
            "status": "started",
            "message": "Routing query to appropriate agent..."
        }

        # Route to appropriate agent
        if self.use_router:
            decision = await self.agent.route(query)
            selected_agent = self.agent.registry.get(decision.agent_id)

            yield {
                "type": "routing",
                "status": "completed",
                "agent_id": decision.agent_id,
                "agent_name": selected_agent.metadata.name if selected_agent else decision.agent_id,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            }

            # Check approval
            requires_approval, approval_reason = selected_agent.requires_approval(
                query=query,
                detected_actions=None,
                context={"session_id": session_id}
            )

            if requires_approval and not approved:
                action = {
                    "action_id": f"action_{session_id}",
                    "action_type": "query_execution",
                    "query": query,
                    "reason": approval_reason or "Query requires approval"
                }
                await self.session_store.request_approval(session_id, action)

                yield {
                    "type": "approval_required",
                    "pending_action": action,
                    "agent_id": decision.agent_id,
                    "agent_name": selected_agent.metadata.name
                }
                return

        else:
            selected_agent = self.agent

        # Build agent request
        history = await self.session_store.get_conversation_history(session_id)
        conversation_history = []
        if history:
            for msg in history.messages[-10:]:  # Last 10 messages
                conversation_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        agent_request = AgentRequest(
            query=query,
            session_id=session_id,
            document_ids=document_ids,
            config={"conversation_history": conversation_history}
        )

        # Stream phase execution
        phase_results = []
        citations = []
        final_answer = ""

        # Get the phase engine from the selected agent
        if self.use_router and selected_agent:
            if hasattr(selected_agent, 'phase_engine'):
                # Financial or custom agent with phase engine
                context = {
                    "query": query,
                    "document_list": ", ".join(document_ids) if document_ids else "All documents",
                    "session_id": session_id
                }

                async for phase_result in selected_agent.phase_engine.execute_phases(context):
                    # Yield phase update
                    phase_event = {
                        "type": "phase",
                        "phase_name": phase_result.phase_name,
                        "phase_type": phase_result.phase_type.value,
                        "status": phase_result.status.value,
                        "output": phase_result.output[:200] if phase_result.output else None  # Preview
                    }
                    logger.info(f"STREAMING: Yielding phase event: {phase_event['phase_name']} - {phase_event['status']}")
                    yield phase_event

                    phase_results.append(phase_result)

                    # Handle retrieval phase
                    if phase_result.phase_name in ["financial_retrieval", "retrieval"]:
                        if hasattr(selected_agent, 'retriever'):
                            retrieved = selected_agent.retriever.retrieve(query, top_k=5)
                            retrieved_context = "\n\n".join([
                                f"[Source: {chunk.chunk.document_id}]\n{chunk.chunk.content}"
                                for chunk in retrieved
                            ])
                            context["retrieved_context"] = retrieved_context
                            citations = [
                                {
                                    "content": chunk.chunk.content[:200] + "...",
                                    "document_id": chunk.chunk.document_id,
                                    "score": chunk.score
                                }
                                for chunk in retrieved
                            ]

                    # Store outputs in context
                    context[f"{phase_result.phase_name}_output"] = phase_result.output

                    # Capture final answer
                    if phase_result.phase_name in ["validation", "reasoning", "risk_assessment"]:
                        final_answer = phase_result.output
            else:
                # Research agent - use default method
                response = await selected_agent.process_query(agent_request)
                final_answer = response.answer
                phase_results = response.phase_results
                citations = response.citations

                # Yield phases from response
                for phase_result in phase_results:
                    yield {
                        "type": "phase",
                        "phase_name": phase_result.phase_name,
                        "phase_type": phase_result.phase_type.value,
                        "status": phase_result.status.value,
                        "output": phase_result.output[:200] if phase_result.output else None
                    }

        # Add assistant response to conversation
        metadata = {
            "citations": citations,
            "phase_count": len(phase_results)
        }
        if self.use_router and selected_agent:
            metadata["agent_id"] = decision.agent_id
            metadata["agent_name"] = selected_agent.metadata.name
            metadata["routing_confidence"] = decision.confidence
            metadata["routing_reasoning"] = decision.reasoning

        await self.session_store.add_message(
            session_id,
            MessageRole.ASSISTANT,
            final_answer,
            metadata=metadata
        )

        # Yield final result
        yield {
            "type": "complete",
            "answer": final_answer,
            "citations": citations,
            "phase_results": [
                {
                    "phase_name": p.phase_name,
                    "phase_type": p.phase_type.value,
                    "status": p.status.value,
                    "output": p.output
                }
                for p in phase_results
            ],
            "agent_id": decision.agent_id if self.use_router else None,
            "agent_name": selected_agent.metadata.name if selected_agent and hasattr(selected_agent, 'metadata') else None,
            "routing_confidence": decision.confidence if self.use_router else None,
            "routing_reasoning": decision.reasoning if self.use_router else None
        }

    async def approve_and_continue(
        self,
        session_id: str,
        action_id: str
    ) -> dict:
        """Approve pending action and continue execution."""
        # Mark action as approved
        await self.session_store.approve_action(session_id, action_id)

        # Get session state
        session_state = await self.session_store.get_session(session_id)
        if not session_state:
            raise ValueError(f"Session not found: {session_id}")

        # Resume graph with approval
        config = {"configurable": {"thread_id": session_state.thread_id}}

        # Update state to mark as approved
        update_state: GraphState = {"approved": True}  # type: ignore

        # Continue execution from checkpoint
        result = await self.graph.ainvoke(update_state, config)

        return result

    async def get_conversation(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> Optional[list[dict]]:
        """Get conversation history."""
        history = await self.session_store.get_conversation_history(session_id, limit)
        if not history:
            return None

        return [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in history.messages
        ]
