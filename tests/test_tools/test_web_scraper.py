from __future__ import annotations

from writing_agent.config import Settings
from writing_agent.tools.web_scraper import Crawl4AIScraper, ScrapeResult


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
