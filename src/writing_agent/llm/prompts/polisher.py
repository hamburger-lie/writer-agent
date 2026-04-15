"""Prompt helpers for the Polisher agent."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult, ResearchResult, ReviewResult


def build_polisher_prompt(
    draft: str,
    plan: PlanResult,
    research: ResearchResult,
    review: ReviewResult | None,
) -> tuple[str, str]:
    """Return prompts for polishing or revising an article draft."""

    system_prompt = (
        "You are the polisher agent for a multi-agent writing system. "
        "Improve clarity, flow, readability, and professional tone while preserving substance."
    )
    review_block = "No prior review feedback. Perform a strong first polish."
    if review is not None:
        review_block = (
            f"Review summary: {review.summary}\n"
            f"Issues: {[issue.model_dump() for issue in review.issues]}\n"
            f"Revision instructions: {review.revision_instructions}"
        )
    user_prompt = f"""Polish this Markdown article.

Title: {plan.title}
Audience: {plan.audience}
Goal: {plan.goal}
Outline: {plan.outline}
Research takeaways: {research.key_takeaways}
Research findings: {[finding.model_dump() for finding in research.findings]}

Current draft:
{draft}

Review guidance:
{review_block}

Requirements:
- keep the Markdown format
- improve flow and readability
- preserve the article's core claims
- incorporate review feedback when present
- return Markdown only
"""
    return system_prompt, user_prompt
