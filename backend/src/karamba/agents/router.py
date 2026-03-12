"""
Agent Router

Automatic intent classification and routing to specialist agents.
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from pydantic import BaseModel

from karamba.agents.base import BaseSpecialistAgent
from karamba.llm import BaseLLM, LLMMessage


class AgentRegistry:
    """Registry for managing specialist agents"""

    def __init__(self):
        self._agents: Dict[str, BaseSpecialistAgent] = {}

    def register(self, agent: BaseSpecialistAgent) -> None:
        """Register a specialist agent"""
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id} ({agent.metadata.name})")

    def get(self, agent_id: str) -> Optional[BaseSpecialistAgent]:
        """Get an agent by ID"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[BaseSpecialistAgent]:
        """List all registered agents"""
        return list(self._agents.values())

    def get_agent_summaries(self) -> List[Dict[str, Any]]:
        """Get summary information about all agents"""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.metadata.name,
                "description": agent.metadata.description,
                "capabilities": [cap.value for cap in agent.metadata.capabilities],
                "keywords": agent.metadata.keywords[:5],  # First 5 keywords
                "example_queries": agent.metadata.example_queries[:2]  # First 2 examples
            }
            for agent in self._agents.values()
        ]


class RouteDecision(BaseModel):
    """Decision about which agent should handle a query"""
    agent_id: str
    confidence: float
    reasoning: str


class AgentRouter:
    """
    Automatic router that classifies user queries and routes them to the appropriate specialist agent.

    Uses LLM-based intent classification combined with rule-based confidence scoring.
    """

    def __init__(self, llm: BaseLLM, registry: AgentRegistry, use_llm_routing: bool = True):
        """
        Initialize the agent router.

        Args:
            llm: Language model for intent classification
            registry: Registry containing available agents
            use_llm_routing: Whether to use LLM for routing (True) or just rule-based (False)
        """
        self.llm = llm
        self.registry = registry
        self.use_llm_routing = use_llm_routing
        logger.info(f"AgentRouter initialized with {len(registry.list_agents())} agents")

    async def route(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RouteDecision:
        """
        Route a query to the most appropriate specialist agent.

        Args:
            query: User's query
            context: Optional context (session history, etc.)

        Returns:
            RouteDecision with agent_id, confidence, and reasoning
        """
        logger.info(f"Routing query: {query[:100]}...")

        agents = self.registry.list_agents()

        if not agents:
            raise ValueError("No agents registered in the router")

        # Strategy 1: Rule-based confidence scoring (fast, always available)
        rule_based_scores = {}
        for agent in agents:
            score = agent.can_handle(query, context)
            rule_based_scores[agent.agent_id] = score
            logger.debug(f"Agent {agent.agent_id} rule-based score: {score:.2f}")

        # Strategy 2: LLM-based intent classification (optional, more accurate)
        if self.use_llm_routing and len(agents) > 1:
            try:
                llm_decision = await self._llm_classify(query, agents, context)

                # Combine LLM decision with rule-based scores
                # Give 70% weight to LLM, 30% to rule-based
                agent_id = llm_decision.agent_id
                combined_confidence = (
                    0.7 * llm_decision.confidence +
                    0.3 * rule_based_scores.get(agent_id, 0.0)
                )

                logger.info(f"LLM routing: {agent_id} (combined confidence: {combined_confidence:.2f})")

                return RouteDecision(
                    agent_id=agent_id,
                    confidence=combined_confidence,
                    reasoning=llm_decision.reasoning
                )

            except Exception as e:
                logger.warning(f"LLM routing failed, falling back to rule-based: {e}")

        # Fallback: Use rule-based scoring only
        best_agent_id = max(rule_based_scores, key=rule_based_scores.get)
        best_score = rule_based_scores[best_agent_id]
        best_agent = self.registry.get(best_agent_id)

        logger.info(f"Rule-based routing: {best_agent_id} (confidence: {best_score:.2f})")

        return RouteDecision(
            agent_id=best_agent_id,
            confidence=best_score,
            reasoning=f"Selected {best_agent.metadata.name} based on keyword matching and query analysis"
        )

    async def _llm_classify(
        self,
        query: str,
        agents: List[BaseSpecialistAgent],
        context: Optional[Dict[str, Any]] = None
    ) -> RouteDecision:
        """
        Use LLM to classify the query and select the best agent.

        Args:
            query: User's query
            agents: List of available agents
            context: Optional context

        Returns:
            RouteDecision from LLM
        """
        # Build agent descriptions
        agent_descriptions = []
        for agent in agents:
            meta = agent.metadata
            desc = f"""
Agent ID: {agent.agent_id}
Name: {meta.name}
Description: {meta.description}
Capabilities: {', '.join([cap.value for cap in meta.capabilities])}
Keywords: {', '.join(meta.keywords[:10])}
Example queries:
{chr(10).join([f"  - {ex}" for ex in meta.example_queries[:3]])}
"""
            agent_descriptions.append(desc)

        # Build classification prompt
        prompt = f"""You are an intelligent query router that selects the most appropriate specialist agent to handle user queries.

Available Agents:
{chr(10).join(agent_descriptions)}

User Query: "{query}"

Analyze the query and determine which agent is best suited to handle it. Consider:
1. The subject matter and domain of the query
2. The type of analysis or task requested
3. The keywords and phrases used
4. The capabilities and expertise of each agent

Respond in the following format:
AGENT_ID: <the agent_id of the best agent>
CONFIDENCE: <confidence score from 0.0 to 1.0>
REASONING: <brief explanation of why this agent was selected>

Example:
AGENT_ID: financial_risk_agent
CONFIDENCE: 0.95
REASONING: Query asks about financial risk assessment which directly matches the Financial Risk Analyst agent's core expertise.
"""

        # Get LLM response
        messages = [LLMMessage(role="user", content=prompt)]
        response = await self.llm.generate(messages)

        # Parse response
        lines = response.content.strip().split('\n')
        agent_id = None
        confidence = 0.0
        reasoning = ""

        for line in lines:
            if line.startswith("AGENT_ID:"):
                agent_id = line.split(":", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                except ValueError:
                    confidence = 0.5
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        # Validate agent_id
        if not agent_id or not self.registry.get(agent_id):
            # LLM returned invalid agent, fall back to first agent
            agent_id = agents[0].agent_id
            confidence = 0.5
            reasoning = "Fallback to default agent due to invalid LLM response"

        return RouteDecision(
            agent_id=agent_id,
            confidence=min(max(confidence, 0.0), 1.0),  # Clamp to [0, 1]
            reasoning=reasoning or f"Selected {agent_id} based on query analysis"
        )

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get information about all available agents"""
        return self.registry.get_agent_summaries()
