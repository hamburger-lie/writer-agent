"""Prompt templates for automatic and human-triggered reflection."""

from __future__ import annotations

from writing_agent.controller.task import ReflectionContext


def build_auto_reflection_prompt(context: ReflectionContext) -> tuple[str, str]:
    """Return prompts for one structured post-run reflection pass."""

    system_prompt = (
        "You are the reflection agent for a multi-agent writing system. "
        "Extract reusable lessons from the most recent pipeline run. "
        "Return JSON only."
    )
    user_prompt = f"""Review this writing pipeline outcome and return valid JSON only.

Topic: {context.topic}
Status: {context.status}
Current stage: {context.current_stage}
Plan title: {context.plan_title}
Review decision: {context.review_decision}
Review summary: {context.review_summary}
Error message: {context.error_message}

Return JSON with:
- summary
- lessons

Requirements:
- lessons must be a list of up to 3 objects
- each lesson object must include reflection_text, category, confidence
- reflection_text must be reusable and not topic-specific
- category should be a short label like evidence, structure, tone, or process
- confidence must be a float between 0 and 1
"""
    return system_prompt, user_prompt
