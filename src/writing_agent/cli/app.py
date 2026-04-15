"""Typer application root."""

from __future__ import annotations

import typer

from writing_agent.cli.commands.config import app as config_app
from writing_agent.cli.commands.edit import edit_command
from writing_agent.cli.commands.history import history_command
from writing_agent.cli.commands.init import init_command
from writing_agent.cli.commands.knowledge import app as knowledge_app
from writing_agent.cli.commands.polish import polish_command
from writing_agent.cli.commands.research import research_command
from writing_agent.cli.commands.review import review_command
from writing_agent.cli.commands.write import write_command


app = typer.Typer(help="Multi-agent writing system CLI.")
app.command("init")(init_command)
app.command("write")(write_command)
app.command("research")(research_command)
app.command("review")(review_command)
app.command("polish")(polish_command)
app.command("edit")(edit_command)
app.command("history")(history_command)
app.add_typer(config_app, name="config")
app.add_typer(knowledge_app, name="knowledge")
