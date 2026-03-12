"""DuckDuckGo search provider implementation."""

import asyncio
from typing import List, Optional
from loguru import logger

from karamba.tools.search.base import SearchProvider, SearchResult


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo web search provider using duckduckgo-search library."""

    def __init__(self):
        super().__init__("duckduckgo")
        self._ddgs = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the DuckDuckGo search client."""
        try:
            from duckduckgo_search import DDGS
            self._ddgs = DDGS()
            logger.info("DuckDuckGo search client initialized successfully")
        except ImportError:
            logger.warning(
                "duckduckgo-search library not installed. "
                "Install with: pip install duckduckgo-search"
            )
            self._ddgs = None
        except Exception as e:
            logger.error(f"Failed to initialize DuckDuckGo client: {e}")
            self._ddgs = None

    def is_available(self) -> bool:
        """Check if DuckDuckGo provider is available."""
        return self._ddgs is not None

    async def search(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        max_retries: int = 2,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform a DuckDuckGo web search with retry logic.

        Args:
            query: The search query
            max_results: Maximum number of results to return
            region: Region code (e.g., "us-en", "wt-wt" for worldwide)
            safesearch: Safe search setting ("on", "moderate", "off")
            max_retries: Maximum number of retries on rate limit
            **kwargs: Additional parameters

        Returns:
            List of SearchResult objects
        """
        if not self.is_available():
            logger.error("DuckDuckGo provider is not available")
            return []

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    logger.info(f"Retry attempt {attempt}/{max_retries}, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    # Recreate client after rate limit
                    self._initialize_client()

                logger.info(f"Searching DuckDuckGo for: {query} (max_results={max_results})")

                # Perform search using duckduckgo-search
                results = []
                raw_results = self._ddgs.text(
                    keywords=query,
                    region=region,
                    safesearch=safesearch,
                    max_results=max_results
                )

                for result in raw_results:
                    search_result = SearchResult(
                        title=result.get("title", ""),
                        url=result.get("href", ""),
                        snippet=result.get("body", ""),
                        source=self.provider_name
                    )
                    results.append(search_result)

                logger.info(f"Found {len(results)} results from DuckDuckGo")
                return results

            except Exception as e:
                error_msg = str(e).lower()

                # Check if it's a rate limit or exception error
                if "ratelimit" in error_msg or "rate limit" in error_msg or "exception occurred" in error_msg:
                    if attempt < max_retries:
                        logger.warning(f"DuckDuckGo error (likely rate limit), will retry after reinitializing client...")
                        continue
                    else:
                        logger.error(f"DuckDuckGo search failed after {max_retries} retries: {e}")
                else:
                    logger.error(f"DuckDuckGo search failed: {e}")

                # Last attempt failed
                if attempt == max_retries:
                    return []
