from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.config import Settings
from writing_agent.storage.manager import StorageManager


def test_history_command_lists_agent_history(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    manager = StorageManager(settings)
    manager.initialize()
    store = manager.get_sqlite_store("writer")
    store.add_task_history(
        task_id="task-1",
        task_type="writer",
        status="success",
        input_summary="AI writing trends",
        output_summary="Draft created",
    )

    result = runner.invoke(app, ["history", "--agent", "writer", "--limit", "5"])

    assert result.exit_code == 0
    assert "task-1" in result.stdout
    assert "Draft created" in result.stdout
