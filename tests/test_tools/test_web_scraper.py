from __future__ import annotations

import httpx

from writing_agent.config import Settings
from writing_agent.tools.web_scraper import Crawl4AIScraper, FirecrawlScraper, ScrapeResult


def test_scraper_sync_entrypoint_returns_normalized_results(monkeypatch) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key")
    scraper = Crawl4AIScraper(settings)

    async def _fake_scrape_many_async(urls: list[str]) -> list[ScrapeResult]:
        return [
            ScrapeResult(
                url="https://example.com",
                title="Example",
                markdown="# Example",
                success=True,
                error=None,
            )
        ]

    monkeypatch.setattr(scraper, "_scrape_many_async", _fake_scrape_many_async)

    results = scraper.scrape_many(["https://example.com"])

    assert results[0].url == "https://example.com"
    assert results[0].success is True


def test_firecrawl_scraper_returns_normalized_results(monkeypatch) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", FIRECRAWL_API_KEY="fc-test-key")

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "success": True,
                "data": {
                    "markdown": "# Example",
                    "metadata": {
                        "title": "Example",
                        "sourceURL": "https://example.com",
                    },
                },
            }

    def _fake_post(*args, **kwargs):
        return _Response()

    monkeypatch.setattr(httpx, "post", _fake_post)

    scraper = FirecrawlScraper(settings)
    results = scraper.scrape_many(["https://example.com"])

    assert results == [
        ScrapeResult(
            url="https://example.com",
            title="Example",
            markdown="# Example",
            success=True,
            error=None,
        )
    ]
