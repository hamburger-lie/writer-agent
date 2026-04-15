from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.config import Settings
from writing_agent.controller.task import SharedFact
from writing_agent.storage.manager import StorageManager


def test_knowledge_search_shared_lists_matching_facts(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    manager = StorageManager(settings)
    manager.initialize()
    shared_store = manager.get_shared_knowledge_store()
    shared_store.upsert_fact(
        SharedFact(
            topic="AI writing trends",
            title="AI Writing Trends in 2026",
            claim="AI tools are mainstream.",
            evidence="Enterprise adoption is broad.",
            source_url="https://example.com/report",
            source_title="Example Report",
            source_snippet="Broad adoption",
            takeaway="AI is mainstream.",
        )
    )

    result = runner.invoke(app, ["knowledge", "search", "enterprise adoption", "--shared"])

    assert result.exit_code == 0
    assert "AI tools are mainstream." in result.stdout
    assert "https://example.com/report" in result.stdout


def test_knowledge_rules_lists_agent_rules(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    manager = StorageManager(settings)
    manager.initialize()
    reviewer_store = manager.get_sqlite_store("reviewer")
    reviewer_store.add_rule(
        rule_text="Always verify claims against cited sources.",
        source="auto_reflection",
        confidence=0.8,
        category="evidence",
    )

    result = runner.invoke(app, ["knowledge", "rules", "--agent", "reviewer"])

    assert result.exit_code == 0
    assert "Always verify claims against" in result.stdout
    assert "cited sources." in result.stdout
    assert "auto_reflection" in result.stdout
