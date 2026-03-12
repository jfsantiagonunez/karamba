"""Tool registry for managing and sharing tools across agents."""

from typing import Dict, Optional, List
from loguru import logger

from karamba.tools.search import WebSearchService, SearchProvider


class ToolRegistry:
    """
    Central registry for managing tools that can be shared across agents.

    Tools are initialized once and can be accessed by any agent that needs them.
    """

    def __init__(self):
        self._tools: Dict[str, any] = {}
        logger.info("ToolRegistry initialized")

    def register_tool(self, tool_name: str, tool_instance: any):
        """
        Register a tool instance.

        Args:
            tool_name: Unique identifier for the tool
            tool_instance: The tool instance to register
        """
        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' already registered, overwriting")

        self._tools[tool_name] = tool_instance
        logger.info(f"Registered tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[any]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance or None if not found
        """
        tool = self._tools.get(tool_name)
        if not tool:
            logger.warning(f"Tool not found: {tool_name}")
        return tool

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self._tools

    def list_tools(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_web_search(self) -> Optional[WebSearchService]:
        """
        Convenience method to get web search service.

        Returns:
            WebSearchService instance or None
        """
        return self.get_tool("web_search")

    def get_code_executor(self):
        """
        Convenience method to get Python code executor.

        Returns:
            PythonExecutor instance or None
        """
        return self.get_tool("code_executor")

    def get_financial_metrics(self):
        """
        Convenience method to get financial metrics calculator.

        Returns:
            FinancialMetrics instance or None
        """
        return self.get_tool("financial_metrics")

    def get_dataframe_tool(self):
        """
        Convenience method to get DataFrame tool.

        Returns:
            DataFrameTool instance or None
        """
        return self.get_tool("dataframe")


def create_tool_registry() -> ToolRegistry:
    """
    Factory function to create and configure a ToolRegistry with default tools.

    Returns:
        Configured ToolRegistry instance
    """
    from karamba.tools.search.duckduckgo import DuckDuckGoProvider
    from karamba.tools.executor import PythonExecutor
    from karamba.tools.finance import FinancialMetrics
    from karamba.tools.data import DataFrameTool

    registry = ToolRegistry()

    # Initialize web search tool
    try:
        web_search = WebSearchService()
        ddg_provider = DuckDuckGoProvider()
        web_search.register_provider(ddg_provider, set_as_default=True)
        registry.register_tool("web_search", web_search)
        logger.info("Web search tool initialized and registered")
    except Exception as e:
        logger.error(f"Failed to initialize web search tool: {e}")

    # Initialize Python code executor
    try:
        code_executor = PythonExecutor(timeout=5, max_output_size=10000)
        registry.register_tool("code_executor", code_executor)
        logger.info("Python code executor initialized and registered")
    except Exception as e:
        logger.error(f"Failed to initialize code executor: {e}")

    # Initialize financial metrics calculator
    try:
        financial_metrics = FinancialMetrics()
        registry.register_tool("financial_metrics", financial_metrics)
        logger.info("Financial metrics calculator initialized and registered")
    except Exception as e:
        logger.error(f"Failed to initialize financial metrics: {e}")

    # Initialize DataFrame tool (with code executor for custom analysis)
    try:
        dataframe_tool = DataFrameTool(code_executor=registry.get_tool("code_executor"))
        registry.register_tool("dataframe", dataframe_tool)
        logger.info("DataFrame tool initialized and registered")
    except Exception as e:
        logger.error(f"Failed to initialize DataFrame tool: {e}")

    return registry
