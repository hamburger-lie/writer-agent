"""CLI commands for inspecting resolved configuration."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from writing_agent.config import get_settings


app = typer.Typer(help="Inspect resolved configuration.")
console = Console()


@app.command("show")
def show_config() -> None:
    """Display normalized runtime settings and validation results."""

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    config_table = Table(title="Resolved Configuration")
    config_table.add_column("Field")
    config_table.add_column("Value")
    config_table.add_row("data_dir", str(settings.data_dir))
    config_table.add_row("deepseek_base_url", settings.deepseek_base_url)
    config_table.add_row("search_engine", settings.search_engine or "<disabled>")
    config_table.add_row("WHITEPAPER_API_URL", settings.whitepaper_api_url or "<unset>")
    console.print(config_table)

    validation_table = Table(title="Validation Report")
    validation_table.add_column("Severity")
    validation_table.add_column("Field")
    validation_table.add_column("Message")
    for item in report.items:
        validation_table.add_row(item.severity.upper(), item.field, item.message)
    console.print(validation_table)
