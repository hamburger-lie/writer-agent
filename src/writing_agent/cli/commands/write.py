"""CLI command for running the Stage 3 planner-to-writer pipeline."""

from __future__ import annotations

import typer
from rich.console import Console

from writing_agent.agents.librarian import LibrarianAgent
from writing_agent.agents.planner import PlannerAgent
from writing_agent.agents.polisher import PolisherAgent
from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.agents.reviewer import ReviewerAgent
from writing_agent.agents.writer import WriterAgent
from writing_agent.config import get_settings
from writing_agent.controller.pipeline import WritingPipeline
from writing_agent.llm.provider import LLMProvider
from writing_agent.reflection.auto_reflect import AutoReflectionEngine
from writing_agent.storage.manager import StorageManager
from writing_agent.tools.web_scraper import Crawl4AIScraper
from writing_agent.tools.web_search import build_search_client


console = Console()


def build_write_pipeline(settings) -> WritingPipeline:
    """Build the planner and writer pipeline with real project services."""

    manager = StorageManager(settings)
    manager.initialize()

    llm_provider = LLMProvider(settings)
    librarian = LibrarianAgent(shared_store=manager.get_shared_knowledge_store())

    planner = PlannerAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("planner"),
        vector_store=manager.get_vector_store("planner"),
        llm_provider=llm_provider,
    )
    researcher = ResearcherAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("researcher"),
        vector_store=manager.get_vector_store("researcher"),
        llm_provider=llm_provider,
        search_client=build_search_client(settings),
        scraper=Crawl4AIScraper(settings),
        librarian=librarian,
    )
    writer = WriterAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("writer"),
        vector_store=manager.get_vector_store("writer"),
        llm_provider=llm_provider,
        librarian=librarian,
    )
    polisher = PolisherAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("polisher"),
        vector_store=manager.get_vector_store("polisher"),
        llm_provider=llm_provider,
    )
    reviewer = ReviewerAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("reviewer"),
        vector_store=manager.get_vector_store("reviewer"),
        llm_provider=llm_provider,
    )
    auto_reflector = AutoReflectionEngine(
        llm_provider=llm_provider,
        sqlite_store=manager.get_sqlite_store("reviewer"),
    )
    return WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=polisher,
        reviewer=reviewer,
        auto_reflector=auto_reflector,
    )


def write_command(topic: str) -> None:
    """Execute the minimum viable planner-to-writer pipeline for a topic."""

    settings = get_settings(clear_cache=True)

    try:
        result = build_write_pipeline(settings).run(topic)
    except Exception as exc:
        console.print(f"[red]write failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"task_id={result.task.task_id}")
    console.print(f"task_dir={result.task.task_dir}")
    console.print(f"plan={result.task.plan_file}")
    console.print(f"research={result.task.research_file}")
    console.print(f"draft={result.task.draft_file}")
    console.print(f"polished={result.task.polished_file}")
    console.print(f"review={result.task.review_file}")
    console.print(f"final={result.task.final_file}")
    console.print("Outline Preview")
    for item in result.plan.outline[:5]:
        console.print(f"- {item}")
    console.print("Draft Preview")
    for line in result.draft.splitlines()[:12]:
        console.print(line)
