from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app


def test_config_show_reports_validation_status(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WHITEPAPER_API_URL", raising=False)

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "data_dir" in result.stdout
    assert "WHITEPAPER_API_URL" in result.stdout
