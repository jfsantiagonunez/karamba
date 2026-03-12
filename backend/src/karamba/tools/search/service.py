"""Web search service that manages multiple search providers."""

from typing import List, Optional, Dict
from loguru import logger

from karamba.tools.search.base import SearchProvider, SearchResult


class WebSearchService:
    """
    Unified web search service that can use multiple providers.

    Supports provider fallback and aggregation strategies.
    """

    def __init__(self, default_provider: Optional[SearchProvider] = None):
        """
        Initialize the web search service.

        Args:
            default_provider: The default search provider to use
        """
        self.providers: Dict[str, SearchProvider] = {}
        self.default_provider_name: Optional[str] = None

        if default_provider:
            self.register_provider(default_provider, set_as_default=True)

        logger.info("WebSearchService initialized")

    def register_provider(
        self,
        provider: SearchProvider,
        set_as_default: bool = False
    ):
        """
        Register a search provider.

        Args:
            provider: The SearchProvider instance to register
            set_as_default: Whether to set this as the default provider
        """
        self.providers[provider.provider_name] = provider
        logger.info(f"Registered search provider: {provider.provider_name}")

        if set_as_default or not self.default_provider_name:
            self.default_provider_name = provider.provider_name
            logger.info(f"Set default provider to: {provider.provider_name}")

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[SearchProvider]:
        """
        Get a search provider by name.

        Args:
            provider_name: Name of the provider, or None for default

        Returns:
            SearchProvider instance or None if not found
        """
        if provider_name is None:
            provider_name = self.default_provider_name

        if not provider_name:
            logger.warning("No provider specified and no default provider set")
            return None

        provider = self.providers.get(provider_name)
        if not provider:
            logger.warning(f"Provider not found: {provider_name}")
            return None

        if not provider.is_available():
            logger.warning(f"Provider {provider_name} is not available")
            return None

        return provider

    async def search(
        self,
        query: str,
        max_results: int = 5,
        provider_name: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform a web search using the specified or default provider.

        Args:
            query: The search query
            max_results: Maximum number of results to return
            provider_name: Name of provider to use (None for default)
            fallback: If True, try other providers if primary fails
            **kwargs: Provider-specific parameters

        Returns:
            List of SearchResult objects
        """
        # Try primary provider
        provider = self.get_provider(provider_name)
        if provider:
            results = await provider.search(query, max_results, **kwargs)
            if results:
                return results
            logger.warning(f"No results from {provider.provider_name}")

        # Try fallback providers if enabled
        if fallback and len(self.providers) > 1:
            logger.info("Attempting fallback to other providers")
            for name, fallback_provider in self.providers.items():
                # Skip the provider we already tried
                if provider and name == provider.provider_name:
                    continue

                if not fallback_provider.is_available():
                    continue

                logger.info(f"Trying fallback provider: {name}")
                results = await fallback_provider.search(query, max_results, **kwargs)
                if results:
                    return results

        logger.warning("All search providers failed or returned no results")
        return []

    def format_results(
        self,
        results: List[SearchResult],
        include_metadata: bool = True
    ) -> str:
        """
        Format search results for LLM consumption.

        Args:
            results: List of search results
            include_metadata: Whether to include metadata like source

        Returns:
            Formatted string
        """
        if not results:
            return "No web search results found."

        formatted = ["## Web Search Results\n"]

        for i, result in enumerate(results, 1):
            formatted.append(f"### {i}. {result.title}")
            formatted.append(f"**URL**: {result.url}")
            formatted.append(f"\n{result.snippet}\n")

            if include_metadata and result.source:
                formatted.append(f"*Source: {result.source}*\n")

        return "\n".join(formatted)

    def list_providers(self) -> List[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return list(self.providers.keys())

    def get_available_providers(self) -> List[str]:
        """
        List all available (ready to use) provider names.

        Returns:
            List of available provider names
        """
        return [
            name for name, provider in self.providers.items()
            if provider.is_available()
        ]
