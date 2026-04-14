from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app


def test_init_command_creates_runtime_layout(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WHITEPAPER_API_URL", raising=False)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / "data" / "agents" / "planner" / "planner.db").exists()
    assert "Initialized 6 agent databases" in result.stdout


def test_init_command_fails_when_core_config_is_missing(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WHITEPAPER_API_URL", raising=False)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "DEEPSEEK_API_KEY" in result.stdout
