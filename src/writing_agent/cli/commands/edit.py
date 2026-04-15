"""CLI command: edit - submit human edits and trigger reflection."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from writing_agent.config import get_settings
from writing_agent.llm.provider import LLMProvider
from writing_agent.reflection.human_reflect import HumanReflectionEngine
from writing_agent.storage.manager import StorageManager


console = Console()


def build_human_reflection_engine(settings) -> HumanReflectionEngine:
    manager = StorageManager(settings)
    manager.initialize()
    return HumanReflectionEngine(
        llm_provider=LLMProvider(settings),
        sqlite_store=manager.get_sqlite_store("writer"),
    )


def edit_command(task_id: str, file: Path) -> None:
    """Submit an edited article and extract reusable human rules."""

    settings = get_settings(clear_cache=True)
    task_dir = settings.data_dir / "tasks" / task_id

    for candidate in ("final.md", "polished.md", "draft.md"):
        original_path = task_dir / candidate
        if original_path.exists():
            break
    else:
        console.print(f"[red]No original draft found for task:[/red] {task_id}")
        raise typer.Exit(code=1)

    original_text = original_path.read_text(encoding="utf-8")
    edited_text = file.read_text(encoding="utf-8")

    try:
        result = build_human_reflection_engine(settings).reflect(
            task_id=task_id,
            original_text=original_text,
            edited_text=edited_text,
        )
    except Exception as exc:
        console.print(f"[red]edit reflection failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"task_id={task_id}")
    console.print(f"rules_added={len(result.rules)}")
