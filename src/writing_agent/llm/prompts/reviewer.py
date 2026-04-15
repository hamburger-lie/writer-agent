"""Prompt helpers for the Reviewer agent."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult, ResearchResult


def build_reviewer_prompt(
    draft: str,
    plan: PlanResult,
    research: ResearchResult,
) -> tuple[str, str]:
    """Return prompts for structured article review."""

    system_prompt = (
        "You are the reviewer agent for a multi-agent writing system. "
        "Evaluate article quality, evidence usage, clarity, and structural fit."
    )
    user_prompt = f"""Review this Markdown article and return valid JSON only.

Title: {plan.title}
Audience: {plan.audience}
Goal: {plan.goal}
Outline: {plan.outline}
Key points: {plan.key_points}
Research takeaways: {research.key_takeaways}

Draft:
{draft}

Return JSON with:
- decision
- summary
- issues
- revision_instructions

Requirements:
- decision must be either "pass" or "fail"
- issues must be a list of objects with severity, title, details
- revision_instructions must be concrete and actionable
"""
    return system_prompt, user_prompt
