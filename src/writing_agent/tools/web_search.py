"""Search engine wrappers used by the researcher stage."""

from __future__ import annotations

import httpx
from pydantic import BaseModel

from writing_agent.config import Settings


class SearchError(RuntimeError):
    """Raised when a search backend cannot return results."""


class SearchConfigurationError(SearchError):
    """Raised when search configuration is incomplete."""


class SearchResult(BaseModel):
    """Normalized search result consumed by the researcher agent."""

    title: str
    url: str
    snippet: str


class SerperSearchClient:
    """Minimal Serper search client using the official HTTP endpoint."""

    endpoint = "https://google.serper.dev/search"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        if not self.settings.search_api_key:
            raise SearchConfigurationError("SEARCH_API_KEY is required for Serper search.")

        response = httpx.post(
            self.endpoint,
            headers={
                "X-API-KEY": self.settings.search_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": limit or self.settings.max_research_urls},
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        organic = payload.get("organic", [])
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            )
            for item in organic
            if item.get("link")
        ]


def build_search_client(settings: Settings):
    """Create the configured search client for the current settings."""

    engine = settings.search_engine or "serper"
    if engine != "serper":
        raise SearchConfigurationError(f"Search engine '{engine}' is not implemented yet.")
    return SerperSearchClient(settings)
