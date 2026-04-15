"""CLI command: history - browse past task history."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from writing_agent.config import AGENT_NAMES, get_settings
from writing_agent.storage.manager import StorageManager


console = Console()


def history_command(
    agent: str = typer.Option(..., "--agent", help="Agent name to inspect."),
    limit: int = typer.Option(10, "--limit", min=1, max=100, help="Number of rows to show."),
) -> None:
    """Show recent task history for one agent database."""

    if agent not in AGENT_NAMES:
        console.print(f"[red]Unknown agent:[/red] {agent}")
        raise typer.Exit(code=1)

    settings = get_settings(clear_cache=True)
    rows = StorageManager(settings).get_sqlite_store(agent).list_task_history(limit=limit)

    table = Table(title=f"{agent} history")
    table.add_column("Task ID")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Created")

    for row in rows:
        table.add_row(
            str(row["task_id"]),
            str(row["task_type"]),
            str(row["status"]),
            str(row["input_summary"] or ""),
            str(row["output_summary"] or ""),
            str(row["created_at"]),
        )

    console.print(table)
