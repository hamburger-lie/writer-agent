"""CLI command: knowledge - manage knowledge bases and rules."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from writing_agent.config import AGENT_NAMES, get_settings
from writing_agent.storage.manager import StorageManager


app = typer.Typer(help="Inspect shared facts and agent rules.")
console = Console()


@app.command("search")
def search_knowledge(
    query: str,
    shared: bool = typer.Option(False, "--shared", help="Search the shared fact library."),
    limit: int = typer.Option(5, "--limit", min=1, max=20, help="Number of results."),
) -> None:
    """Search the shared knowledge library."""

    if not shared:
        console.print("[red]Only --shared search is implemented right now.[/red]")
        raise typer.Exit(code=1)

    settings = get_settings(clear_cache=True)
    store = StorageManager(settings).get_shared_knowledge_store()
    results = store.search(query.split(), limit=limit)

    table = Table(title="Shared knowledge search")
    table.add_column("Claim")
    table.add_column("Takeaway")
    table.add_column("Source")
    for fact in results:
        table.add_row(fact.claim, fact.takeaway, fact.source_url)
    console.print(table)


@app.command("rules")
def list_rules(
    agent: str = typer.Option(..., "--agent", help="Agent name to inspect."),
) -> None:
    """List active rules for one agent."""

    if agent not in AGENT_NAMES:
        console.print(f"[red]Unknown agent:[/red] {agent}")
        raise typer.Exit(code=1)

    settings = get_settings(clear_cache=True)
    rows = StorageManager(settings).get_sqlite_store(agent).list_active_rules()

    table = Table(title=f"{agent} rules")
    table.add_column("Rule")
    table.add_column("Source")
    table.add_column("Confidence")
    table.add_column("Category")
    for row in rows:
        table.add_row(
            str(row["rule_text"]),
            str(row["source"]),
            str(row["confidence"]),
            str(row["category"] or ""),
        )
    console.print(table)
