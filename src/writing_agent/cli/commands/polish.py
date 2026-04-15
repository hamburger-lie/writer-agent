"""CLI command: polish - refine an existing draft."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from writing_agent.agents.polisher import PolisherAgent
from writing_agent.cli.commands.common import load_or_build_context
from writing_agent.config import get_settings
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.manager import StorageManager


console = Console()


def build_polisher_agent(settings) -> PolisherAgent:
    manager = StorageManager(settings)
    manager.initialize()
    llm_provider = LLMProvider(settings)
    return PolisherAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("polisher"),
        vector_store=manager.get_vector_store("polisher"),
        llm_provider=llm_provider,
    )


def polish_command(
    file: Path,
    output: Path | None = typer.Option(None, "--output", help="Where to write polished markdown"),
) -> None:
    """Polish a Markdown draft file."""

    settings = get_settings(clear_cache=True)
    draft = file.read_text(encoding="utf-8")
    plan, research = load_or_build_context(file)

    try:
        polished = build_polisher_agent(settings).run(draft, plan, research, review=None)
    except Exception as exc:
        console.print(f"[red]polish failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    output_path = output or file.with_name(f"{file.stem}.polished.md")
    output_path.write_text(polished, encoding="utf-8")
    console.print(f"output={output_path}")
