"""Prompt helpers for the Planner agent."""

from __future__ import annotations


def build_planner_prompt(topic: str) -> tuple[str, str]:
    """Return the planner system and user prompts for a topic."""

    system_prompt = (
        "You are the planner agent for a multi-agent writing system. "
        "Produce clear, practical article plans for professional readers."
    )
    user_prompt = f"""Create a structured writing plan for this topic: {topic}

Return valid JSON only with these fields:
- topic
- audience
- goal
- title
- outline
- key_points
- constraints
- research_questions

Requirements:
- outline must be an ordered list of section headings
- key_points must be concrete article points to cover
- constraints must be a list of tone or writing limits
- research_questions should be useful for a future research phase
"""
    return system_prompt, user_prompt
