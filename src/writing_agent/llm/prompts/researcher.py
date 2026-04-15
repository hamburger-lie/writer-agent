"""Prompt helpers for the Researcher agent."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult
from writing_agent.tools.web_scraper import ScrapeResult
from writing_agent.tools.web_search import SearchResult


def build_research_query_prompt(plan: PlanResult) -> tuple[str, str]:
    """Return prompts for generating concrete search queries from a plan."""

    system_prompt = (
        "You are the researcher agent for a multi-agent writing system. "
        "Turn article plans into focused web search queries."
    )
    user_prompt = f"""Generate a compact list of web search queries for this article plan.

Topic: {plan.topic}
Title: {plan.title}
Audience: {plan.audience}
Goal: {plan.goal}
Research questions: {plan.research_questions}

Return valid JSON only with this field:
- queries

Requirements:
- 2 to 4 queries
- queries should be concrete and web-search friendly
- cover the strongest research questions first
"""
    return system_prompt, user_prompt


def build_research_summary_prompt(
    plan: PlanResult,
    search_queries: list[str],
    search_results: list[SearchResult],
    scraped_pages: list[ScrapeResult],
) -> tuple[str, str]:
    """Return prompts for summarizing search and scrape results into structured research."""

    system_prompt = (
        "You are the researcher agent for a multi-agent writing system. "
        "Summarize researched material into structured findings for a writer."
    )
    rendered_sources = "\n".join(
        f"- {item.title} | {item.url} | {item.snippet}" for item in search_results
    )
    rendered_pages = "\n\n".join(
        f"URL: {item.url}\nTitle: {item.title}\nMarkdown:\n{item.markdown[:4000]}"
        for item in scraped_pages
    )
    user_prompt = f"""Summarize this research for the article plan below.

Topic: {plan.topic}
Title: {plan.title}
Outline: {plan.outline}
Key points: {plan.key_points}
Constraints: {plan.constraints}
Search queries: {search_queries}

Search results:
{rendered_sources}

Scraped pages:
{rendered_pages}

Return valid JSON only with these fields:
- topic
- search_queries
- sources
- findings
- key_takeaways
- open_questions

Requirements:
- sources must be a list of objects with title, url, snippet, fetched_at
- findings must be a list of objects with claim, evidence, source_url
- do not return sources as plain strings
- do not return findings as a nested object
"""
    return system_prompt, user_prompt
