"""
Research Agent

Specialist agent for general research and document Q&A.
Wraps the existing KarambaAgent with the specialist agent interface.
"""

from typing import Dict, Any, Optional
from loguru import logger

from karamba.agents.base import AgentCapability, AgentMetadata, ApprovalPolicy
from karamba.agents.tool_aware import ToolAwareAgent
from karamba.core.agent import KarambaAgent
from karamba.core.models import AgentRequest, AgentResponse
from karamba.llm import LLMConfig


class ResearchAgent(ToolAwareAgent):
    """
    Specialist agent for research tasks and document question-answering.

    Capabilities:
    - General research questions
    - Document Q&A
    - Summarization
    - Information synthesis
    """

    def __init__(
        self,
        agent_id: str = "research_agent",
        llm_config: Optional[LLMConfig] = None,
        reasoning_llm_config: Optional[LLMConfig] = None,
        vector_store_path: str = "./vector_store",
        enable_reflection: bool = False,
        # Automatic tool injection via ToolAwareAgent
        search_service=None,
        dataframe_tool=None,
        code_executor=None,
        financial_metrics=None,
        upload_dir: str = "./data/uploads"
    ):
        # Initialize ToolAwareAgent with automatic tool support
        super().__init__(
            agent_id=agent_id,
            enable_reflection=enable_reflection,
            search_service=search_service,
            dataframe_tool=dataframe_tool,
            code_executor=code_executor,
            financial_metrics=financial_metrics,
            upload_dir=upload_dir
        )

        # Initialize the underlying Karamba agent
        if llm_config is None:
            llm_config = LLMConfig(
                provider="ollama",
                model_name="llama3.2:latest"
            )

        self.karamba_agent = KarambaAgent(
            llm_config=llm_config,
            reasoning_llm_config=reasoning_llm_config,  # Pass Claude for complex reasoning
            vector_store_path=vector_store_path
        )

        # Log available tools (from ToolAwareAgent)
        available_tools = self.get_available_tools()
        logger.info(f"ResearchAgent initialized with tools: {available_tools}")

    @property
    def metadata(self) -> AgentMetadata:
        """Return metadata describing this agent's capabilities"""
        return AgentMetadata(
            name="Research Assistant",
            description="General-purpose research agent for document Q&A, information synthesis, and knowledge extraction",
            capabilities=[
                AgentCapability.RESEARCH,
                AgentCapability.DOCUMENT_QA,
                AgentCapability.SUMMARIZATION
            ],
            keywords=[
                "research", "question", "what", "how", "why", "explain",
                "summarize", "describe", "tell me about", "information",
                "analyze", "compare", "overview", "details", "background"
            ],
            example_queries=[
                "What are the key findings in the research papers?",
                "Explain the concept of quantum computing",
                "Summarize the main points from the uploaded documents",
                "How does machine learning work?",
                "Compare the different approaches mentioned in the papers"
            ],
            approval_policy=ApprovalPolicy(
                requires_approval=False,  # Research queries don't need approval by default
                approval_triggers=["delete", "remove"],  # But deletion operations do
                risky_actions=["delete_document", "clear_data"]
            )
        )

    async def process_query(
        self,
        request: AgentRequest,
        session_context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Process a research query using the Karamba agent.

        Args:
            request: The incoming agent request
            session_context: Optional session context (conversation history, etc.)

        Returns:
            AgentResponse with the research result
        """
        logger.info(f"=== RESEARCH_AGENT.PROCESS_QUERY CALLED ===")
        logger.info(f"ResearchAgent processing query: {request.query}")
        logger.info(f"Document IDs: {request.document_ids}")

        # 🎯 AUTOMATIC TOOL ROUTING - Get tools based on query and documents
        tool_results = await self.process_query_with_tools(request)
        logger.info(f"Automatic tool routing used: {list(tool_results.keys())}")

        # Add session context if available
        if session_context:
            logger.debug(f"Session context available: {list(session_context.keys())}")

        # Enhance request with tool results
        # If dataframe tool was used, log it
        if "dataframe" in tool_results:
            logger.info(f"DataFrameTool results available: {tool_results['dataframe']['summary'][:200]}...")

        # If web search was used, log it
        if "web_search" in tool_results:
            logger.info(f"Web search results available: {tool_results['web_search']['result_count']} results")

        # Pass tool results to KarambaAgent via request.config
        if tool_results:
            request.config["tool_results"] = tool_results
            logger.info(f"Passing tool results to KarambaAgent: {list(tool_results.keys())}")

        # Use the underlying Karamba agent to process the query
        logger.info(f"About to call karamba_agent.answer_question")
        response = await self.karamba_agent.answer_question(request)
        logger.info(f"karamba_agent.answer_question returned")

        logger.info(f"KarambaAgent returned answer: {len(response.answer) if response.answer else 0} chars")
        logger.info(f"Answer preview: {response.answer[:200] if response.answer else '(empty)'}")

        # Add agent metadata to response
        response.metadata = response.metadata or {}
        response.metadata["agent_id"] = self.agent_id
        response.metadata["agent_type"] = "research"
        response.metadata["tools_used"] = list(tool_results.keys())  # Track which tools were used

        logger.info(f"ResearchAgent completed query processing with tools: {list(tool_results.keys())}")
        return response

    def can_handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given query.

        Research agent is the generalist fallback, so it has moderate confidence
        for most queries unless they contain specific financial/risk keywords.

        Args:
            query: The user's query
            context: Optional context about the query

        Returns:
            Confidence score (0.0 to 1.0)
        """
        query_lower = query.lower()

        # High confidence for research-specific keywords
        research_keywords = ["what", "how", "why", "explain", "summarize", "describe"]
        high_confidence_keywords = ["research", "information", "tell me about"]

        # Lower confidence for financial-specific queries
        financial_keywords = ["risk", "financial", "investment", "portfolio", "return",
                             "volatility", "sharpe", "var", "equity", "stock", "bonds"]

        # Count keyword matches
        research_score = sum(1 for kw in research_keywords if kw in query_lower)
        high_score = sum(1 for kw in high_confidence_keywords if kw in query_lower)
        financial_score = sum(1 for kw in financial_keywords if kw in query_lower)

        # If financial keywords are dominant, lower confidence
        if financial_score > 2:
            return 0.3

        # If research keywords are present, higher confidence
        if high_score > 0:
            return 0.9
        if research_score > 1:
            return 0.8

        # Default moderate confidence (generalist fallback)
        return 0.6

    async def ingest_document(self, file_path, file_content=None):
        """Proxy method to ingest documents into the underlying agent"""
        return await self.karamba_agent.ingest_document(file_path, file_content)

    def get_document_stats(self):
        """Proxy method to get document statistics"""
        return self.karamba_agent.get_document_stats()

    def delete_document(self, document_id: str):
        """Proxy method to delete documents"""
        self.karamba_agent.delete_document(document_id)
