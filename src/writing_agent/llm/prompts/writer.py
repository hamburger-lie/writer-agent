"""Prompt helpers for the Writer agent."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult


def build_writer_prompt(plan: PlanResult) -> tuple[str, str]:
    """Return the writer system and user prompts for a plan."""

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

Requirements:
- use the title as the H1 heading
- include a short introduction
- cover each outline section
- include a short conclusion
- return Markdown only
"""
    return system_prompt, user_prompt
