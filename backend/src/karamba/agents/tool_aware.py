"""Tool-aware agent base class with automatic tool routing.

All agents inherit from this to automatically get:
- Intelligent tool selection based on query and document types
- Automatic routing to DataFrameTool, web search, code executor, etc.
- No manual integration needed!
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger

from karamba.agents.base import BaseSpecialistAgent
from karamba.core.models import AgentRequest


class DocumentContext:
    """Information about documents in the session."""
    def __init__(self):
        self.has_tabular = False
        self.has_text = False
        self.tabular_files: List[str] = []
        self.text_files: List[str] = []


class ToolAwareAgent(BaseSpecialistAgent):
    """
    Base class for agents with automatic tool routing.

    Agents inherit from this and automatically get:
    - DataFrameTool for Excel/CSV
    - Web search for current information
    - Code executor for custom calculations
    - Financial metrics for standard calculations

    The agent automatically decides which tool to use based on:
    - Document types in the session
    - Query intent (keywords, patterns)
    - Available tools
    """

    def __init__(
        self,
        agent_id: str,
        enable_reflection: bool = False,
        # Optional tools (injected via registry)
        dataframe_tool=None,
        code_executor=None,
        financial_metrics=None,
        search_service=None,
        upload_dir: str = "./data/uploads"
    ):
        super().__init__(agent_id, enable_reflection)

        # Store tools (optional - graceful fallback if not provided)
        self.dataframe_tool = dataframe_tool
        self.code_executor = code_executor
        self.financial_metrics = financial_metrics
        self.search_service = search_service

        # Store upload directory for document resolution
        self.upload_dir = Path(upload_dir)

        # Log available tools
        available_tools = []
        if dataframe_tool:
            available_tools.append("dataframe")
        if code_executor:
            available_tools.append("code_executor")
        if financial_metrics:
            available_tools.append("financial_metrics")
        if search_service:
            available_tools.append("web_search")

        logger.info(f"{agent_id} initialized with tools: {available_tools or 'none'}")

    # Automatic Tool Detection

    def _detect_document_context(self, request: AgentRequest) -> DocumentContext:
        """
        Automatically detect document types in the session.

        This would query document metadata to see if tabular or text docs exist.

        Args:
            request: Agent request with document IDs

        Returns:
            DocumentContext with information about document types
        """
        context = DocumentContext()

        # TODO: Query document metadata to detect types
        # For now, detect based on filenames
        if request.document_ids:
            for doc_id in request.document_ids:
                # Simple heuristic (replace with actual metadata query)
                if doc_id.endswith(('.xlsx', '.xls', '.csv')):
                    context.has_tabular = True
                    context.tabular_files.append(doc_id)
                else:
                    context.has_text = True
                    context.text_files.append(doc_id)

        logger.info(f"Document context: tabular={context.has_tabular}, text={context.has_text}")
        return context

    def _query_needs_tabular_analysis(self, query: str) -> bool:
        """
        Detect if query requires tabular data operations.

        Args:
            query: User query

        Returns:
            True if query likely needs DataFrameTool
        """
        tabular_keywords = [
            # Operations
            "calculate", "compute", "aggregate", "sum", "average", "mean",
            "filter", "group by", "count", "total", "max", "min",
            # Data analysis
            "statistics", "correlation", "trend", "distribution",
            # Financial metrics
            "sharpe", "var", "value at risk", "volatility", "return",
            "portfolio", "returns", "performance", "risk metrics",
            # Table operations
            "compare", "rank", "sort", "top", "bottom"
        ]

        query_lower = query.lower()
        matches = [kw for kw in tabular_keywords if kw in query_lower]

        if matches:
            logger.info(f"Query matches tabular keywords: {matches}")
            return True

        return False

    def _query_needs_web_search(self, query: str) -> bool:
        """
        Detect if query needs current web information.

        Args:
            query: User query

        Returns:
            True if query needs web search
        """
        web_keywords = [
            "current", "latest", "recent", "today", "now",
            "news", "market", "price", "stock", "updated"
        ]

        query_lower = query.lower()
        return any(kw in query_lower for kw in web_keywords)

    def _query_needs_calculation(self, query: str) -> bool:
        """
        Detect if query needs custom calculation.

        Args:
            query: User query

        Returns:
            True if query needs code executor
        """
        calc_keywords = [
            "calculate", "compute", "simulate", "model",
            "forecast", "predict", "estimate"
        ]

        query_lower = query.lower()
        return any(kw in query_lower for kw in calc_keywords)

    # Automatic Tool Routing

    async def _route_to_dataframe_tool(
        self,
        request: AgentRequest,
        doc_context: DocumentContext
    ) -> Optional[Any]:
        """
        Automatically handle tabular data queries.

        Args:
            request: Agent request
            doc_context: Document context

        Returns:
            Analysis result or None if tool not available
        """
        if not self.dataframe_tool:
            logger.warning("DataFrameTool requested but not available")
            return None

        logger.info("Routing to DataFrameTool for tabular analysis")

        try:
            # Load tabular files
            for doc_id in doc_context.tabular_files:
                # Resolve document ID to full file path
                file_path = self.upload_dir / doc_id
                logger.info(f"Resolving document ID '{doc_id}' to path: {file_path}")

                if not file_path.exists():
                    logger.error(f"File not found: {file_path}")
                    continue

                if doc_id.endswith('.xlsx') or doc_id.endswith('.xls'):
                    result = self.dataframe_tool.load_excel(str(file_path))
                elif doc_id.endswith('.csv'):
                    result = self.dataframe_tool.load_csv(str(file_path))

                if not result.success:
                    logger.error(f"Failed to load {doc_id}: {result.error}")

            # Get summary (LLM-safe, not raw data!)
            summary = self.dataframe_tool.get_summary()

            return {
                "tool": "dataframe",
                "summary": summary.summary,
                "data_available": True
            }

        except Exception as e:
            logger.error(f"DataFrameTool routing failed: {e}")
            return None

    async def _route_to_web_search(self, request: AgentRequest) -> Optional[Any]:
        """
        Automatically perform web search.

        Args:
            request: Agent request

        Returns:
            Search results or None
        """
        if not self.search_service:
            logger.warning("Web search requested but not available")
            return None

        logger.info("Routing to web search for current information")

        try:
            results = await self.search_service.search(
                request.query,
                max_results=5
            )

            formatted = self.search_service.format_results(results)

            return {
                "tool": "web_search",
                "results": formatted,
                "result_count": len(results)
            }

        except Exception as e:
            logger.error(f"Web search routing failed: {e}")
            return None

    async def _route_to_metrics(self, metric_name: str, data: List[float]) -> Optional[Any]:
        """
        Automatically calculate financial metrics.

        Args:
            metric_name: Name of metric to calculate
            data: Data to analyze

        Returns:
            Metric result or None
        """
        if not self.financial_metrics:
            logger.warning("Financial metrics requested but not available")
            return None

        logger.info(f"Routing to financial metrics: {metric_name}")

        try:
            if metric_name == "sharpe_ratio":
                result = self.financial_metrics.sharpe_ratio(data)
            elif metric_name == "volatility":
                result = self.financial_metrics.volatility(data)
            elif metric_name == "var":
                result = self.financial_metrics.value_at_risk(data)
            else:
                return None

            return {
                "tool": "financial_metrics",
                "metric": metric_name,
                "value": result.value,
                "metadata": result.metadata
            }

        except Exception as e:
            logger.error(f"Metrics calculation failed: {e}")
            return None

    # Main Processing with Automatic Routing

    async def process_query_with_tools(self, request: AgentRequest) -> Dict[str, Any]:
        """
        Process query with automatic tool routing.

        Subclasses can call this to get automatic tool support.

        Args:
            request: Agent request

        Returns:
            Dictionary with tool results
        """
        tool_results = {}

        # Detect document context
        doc_context = self._detect_document_context(request)

        # Smart routing for tabular data:
        # 1. If query explicitly needs tabular analysis (calculate, aggregate, etc.) → use tool
        # 2. If tabular file present AND query asks about files/data → use tool
        needs_explicit_tabular = self._query_needs_tabular_analysis(request.query)
        asking_about_files = any(word in request.query.lower() for word in
                                 ["file", "upload", "document", "data", "sheet", "excel", "csv"])

        if doc_context.has_tabular and (needs_explicit_tabular or asking_about_files):
            logger.info(f"Routing to DataFrameTool: explicit={needs_explicit_tabular}, asking_about_files={asking_about_files}")
            df_result = await self._route_to_dataframe_tool(request, doc_context)
            if df_result:
                tool_results["dataframe"] = df_result

        if self._query_needs_web_search(request.query):
            web_result = await self._route_to_web_search(request)
            if web_result:
                tool_results["web_search"] = web_result

        logger.info(f"Tool routing complete: used {list(tool_results.keys())}")
        return tool_results

    # Utility Methods

    def get_available_tools(self) -> List[str]:
        """Get list of available tools for this agent."""
        tools = []
        if self.dataframe_tool:
            tools.append("dataframe")
        if self.code_executor:
            tools.append("code_executor")
        if self.financial_metrics:
            tools.append("financial_metrics")
        if self.search_service:
            tools.append("web_search")
        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if specific tool is available."""
        return tool_name in self.get_available_tools()
