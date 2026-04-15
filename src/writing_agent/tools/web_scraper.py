"""Crawl4AI wrapper used by the researcher stage."""

from __future__ import annotations

import asyncio
import httpx

from pydantic import BaseModel

from writing_agent.config import Settings


class ScraperError(RuntimeError):
    """Raised when scraping cannot be completed."""


class ScrapeResult(BaseModel):
    """Normalized scrape result consumed by the researcher agent."""

    url: str
    title: str
    markdown: str
    success: bool
    error: str | None = None


class Crawl4AIScraper:
    """Thin synchronous wrapper around Crawl4AI async scraping."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def scrape_many(self, urls: list[str]) -> list[ScrapeResult]:
        return asyncio.run(self._scrape_many_async(urls))

    async def _scrape_many_async(self, urls: list[str]) -> list[ScrapeResult]:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        except ImportError as exc:
            raise ScraperError("crawl4ai is required for web scraping.") from exc

        browser_config = BrowserConfig(headless=True)
        run_config = CrawlerRunConfig()

        results: list[ScrapeResult] = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawl_results = await crawler.arun_many(urls=urls, config=run_config)
            for item in crawl_results:
                markdown = getattr(item, "markdown", None)
                markdown_content = ""
                if isinstance(markdown, str):
                    markdown_content = markdown
                elif markdown is not None:
                    markdown_content = getattr(markdown, "fit_markdown", "") or getattr(
                        markdown, "raw_markdown", ""
                    )

                results.append(
                    ScrapeResult(
                        url=str(getattr(item, "url", "")),
                        title=str(getattr(item, "title", "") or ""),
                        markdown=markdown_content,
                        success=bool(getattr(item, "success", False)),
                        error=getattr(item, "error_message", None),
                    )
                )

        return results


class FirecrawlScraper:
    """HTTP scraper backed by Firecrawl's scrape endpoint."""

    endpoint = "https://api.firecrawl.dev/v2/scrape"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def scrape_many(self, urls: list[str]) -> list[ScrapeResult]:
        if not self.settings.firecrawl_api_key:
            raise ScraperError("FIRECRAWL_API_KEY is required for Firecrawl scraping.")

        results: list[ScrapeResult] = []
        for url in urls:
            response = httpx.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.settings.firecrawl_api_key}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "formats": ["markdown"]},
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", {})
            metadata = data.get("metadata", {})
            results.append(
                ScrapeResult(
                    url=str(metadata.get("sourceURL", url)),
                    title=str(metadata.get("title", "") or ""),
                    markdown=str(data.get("markdown", "") or ""),
                    success=bool(payload.get("success", False)),
                    error=None,
                )
            )
        return results


def build_scraper(settings: Settings):
    """Create the configured scraper backend for the current settings."""

    if settings.search_engine == "firecrawl":
        return FirecrawlScraper(settings)
    return Crawl4AIScraper(settings)
