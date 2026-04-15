"""CLI command: research - standalone research execution."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from writing_agent.agents.librarian import LibrarianAgent
from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.config import get_settings
from writing_agent.controller.task import PlanResult
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.manager import StorageManager
from writing_agent.tools.web_scraper import build_scraper
from writing_agent.tools.web_search import build_search_client


console = Console()


def build_research_agent(settings) -> ResearcherAgent:
    manager = StorageManager(settings)
    manager.initialize()
    llm_provider = LLMProvider(settings)
    librarian = LibrarianAgent(shared_store=manager.get_shared_knowledge_store())
    return ResearcherAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("researcher"),
        vector_store=manager.get_vector_store("researcher"),
        llm_provider=llm_provider,
        search_client=build_search_client(settings),
        scraper=build_scraper(settings),
        librarian=librarian,
    )


def research_command(
    topic: str,
    output: Path | None = typer.Option(None, "--output", help="Where to write research.json"),
) -> None:
    """Run standalone research for a topic and persist the structured result."""

    settings = get_settings(clear_cache=True)
    agent = build_research_agent(settings)
    plan = PlanResult(
        topic=topic,
        audience="general readers",
        goal=f"research {topic}",
        title=topic,
        outline=["Overview"],
        key_points=[],
        constraints=[],
        research_questions=[topic],
    )

    try:
        result = agent.run(plan)
    except Exception as exc:
        console.print(f"[red]research failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    output_path = output or (settings.data_dir / "exports" / "research.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"topic={result.topic}")
    console.print(f"output={output_path}")
