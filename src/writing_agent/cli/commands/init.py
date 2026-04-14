"""CLI command for initializing runtime directories and databases."""

from __future__ import annotations

import typer
from rich.console import Console

from writing_agent.config import ValidationSeverity, get_settings
from writing_agent.storage.manager import StorageManager


console = Console()


def init_command() -> None:
    """Initialize data directories, per-agent databases, and report config health."""

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    if report.has_errors:
        for item in report.items:
            style = "red" if item.severity == ValidationSeverity.ERROR else "yellow"
            console.print(f"[{style}]{item.severity.upper()}[/{style}] {item.field}: {item.message}")
        raise typer.Exit(code=1)

    result = StorageManager(settings).initialize()
    console.print(f"[green]Initialized {len(result.initialized_agents)} agent databases[/green]")

    for item in report.items:
        style = "yellow" if item.severity == ValidationSeverity.WARNING else "green"
        console.print(f"[{style}]{item.severity.upper()}[/{style}] {item.field}: {item.message}")
