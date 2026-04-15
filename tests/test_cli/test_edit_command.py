from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.config import Settings
from writing_agent.storage.manager import StorageManager


class _FakeHumanReflectionEngine:
    def reflect(self, *, task_id: str, original_text: str, edited_text: str):
        return None


def test_edit_command_reads_task_file_and_updates_writer_rules(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    manager = StorageManager(settings)
    manager.initialize()

    task_dir = settings.data_dir / "tasks" / "task-123"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "final.md").write_text("# Draft\n\nOriginal text.", encoding="utf-8")

    edited_path = tmp_path / "edited.md"
    edited_path.write_text("# Draft\n\nEdited text.", encoding="utf-8")

    called: dict[str, str] = {}

    class _Engine:
        def reflect(self, *, task_id: str, original_text: str, edited_text: str):
            called["task_id"] = task_id
            called["original_text"] = original_text
            called["edited_text"] = edited_text
            return type("Result", (), {"rules": ["rule-1"]})()

    monkeypatch.setattr("writing_agent.cli.commands.edit.build_human_reflection_engine", lambda settings: _Engine())

    result = runner.invoke(app, ["edit", "task-123", str(edited_path)])

    assert result.exit_code == 0
    assert called["task_id"] == "task-123"
    assert "Original text." in called["original_text"]
    assert "Edited text." in called["edited_text"]
