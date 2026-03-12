"""Base classes for web search providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from loguru import logger


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: str
    source: str  # Provider name (e.g., "duckduckgo", "tavily")
    relevance_score: Optional[float] = None

    def __str__(self) -> str:
        return f"[{self.title}]({self.url})\n{self.snippet}"


class SearchProvider(ABC):
    """Abstract base class for web search providers."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        logger.info(f"Initialized {provider_name} search provider")

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform a web search.

        Args:
            query: The search query
            max_results: Maximum number of results to return
            **kwargs: Provider-specific parameters

        Returns:
            List of SearchResult objects
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and properly configured.

        Returns:
            True if provider is ready to use, False otherwise
        """
        pass

    def format_results(self, results: List[SearchResult]) -> str:
        """
        Format search results as a string for LLM consumption.

        Args:
            results: List of search results

        Returns:
            Formatted string
        """
        if not results:
            return "No search results found."

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. **{result.title}**\n"
                f"   Source: {result.url}\n"
                f"   {result.snippet}\n"
            )

        return "\n".join(formatted)
