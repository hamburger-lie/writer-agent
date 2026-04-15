"""Prompt helpers for the Writer agent."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult, ResearchResult, SharedFact


def build_writer_prompt(
    plan: PlanResult,
    research: ResearchResult,
    shared_facts: list[SharedFact] | None = None,
) -> tuple[str, str]:
    """Return the writer system and user prompts for a plan."""

    shared_facts = shared_facts or []
    system_prompt = (
        "You are the writer agent for a multi-agent writing system. "
        "Write complete, readable, professional Markdown drafts."
    )
    user_prompt = f"""Write a complete Markdown article from this plan.

Title: {plan.title}
Audience: {plan.audience}
Goal: {plan.goal}
Outline: {plan.outline}
Key points: {plan.key_points}
Constraints: {plan.constraints}
Research takeaways: {research.key_takeaways}
Research findings: {[finding.model_dump() for finding in research.findings]}
Research sources: {[source.url for source in research.sources]}
Shared knowledge facts: {[fact.model_dump() for fact in shared_facts]}

Requirements:
- use the title as the H1 heading
- include a short introduction
- cover each outline section
- include a short conclusion
- incorporate the research takeaways and findings
- return Markdown only
"""
    return system_prompt, user_prompt
