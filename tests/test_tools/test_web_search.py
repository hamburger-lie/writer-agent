from __future__ import annotations

import httpx

from writing_agent.config import Settings
from writing_agent.tools.web_search import SearchResult, SerperSearchClient


def test_serper_search_client_parses_organic_results(monkeypatch) -> None:
    settings = Settings(
        DEEPSEEK_API_KEY="test-key",
        SEARCH_ENGINE="serper",
        SEARCH_API_KEY="search-key",
    )

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "organic": [
                    {
                        "title": "Example",
                        "link": "https://example.com",
                        "snippet": "Example snippet",
                    }
                ]
            }

    def _fake_post(*args, **kwargs):
        return _Response()

    monkeypatch.setattr(httpx, "post", _fake_post)

    client = SerperSearchClient(settings)
    results = client.search("ai writing trends")

    assert results == [
        SearchResult(title="Example", url="https://example.com", snippet="Example snippet")
    ]
