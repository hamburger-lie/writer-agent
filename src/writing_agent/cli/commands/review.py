"""CLI command: review - review an existing draft."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from writing_agent.agents.reviewer import ReviewerAgent
from writing_agent.cli.commands.common import load_or_build_context
from writing_agent.config import get_settings
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.manager import StorageManager


console = Console()


def build_reviewer_agent(settings) -> ReviewerAgent:
    manager = StorageManager(settings)
    manager.initialize()
    llm_provider = LLMProvider(settings)
    return ReviewerAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("reviewer"),
        vector_store=manager.get_vector_store("reviewer"),
        llm_provider=llm_provider,
    )


def review_command(file: Path) -> None:
    """Review a Markdown draft file."""

    settings = get_settings(clear_cache=True)
    draft = file.read_text(encoding="utf-8")
    plan, research = load_or_build_context(file)

    try:
        review = build_reviewer_agent(settings).run(draft, plan, research)
    except Exception as exc:
        console.print(f"[red]review failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"decision={review.decision}")
    console.print(f"summary={review.summary}")
