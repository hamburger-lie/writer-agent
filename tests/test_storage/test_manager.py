from __future__ import annotations

from pathlib import Path

import pytest

from writing_agent.config import get_settings
from writing_agent.storage.manager import StorageManager


def test_storage_manager_initializes_all_agent_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    settings = get_settings(clear_cache=True)

    manager = StorageManager(settings)
    result = manager.initialize()

    assert (settings.data_dir / "shared" / "chroma").exists()
    assert (settings.data_dir / "tasks").exists()
    assert (settings.data_dir / "exports").exists()
    assert len(result.initialized_agents) == 6
    assert (settings.data_dir / "agents" / "planner" / "planner.db").exists()


def test_storage_manager_writes_agent_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    settings = get_settings(clear_cache=True)

    manager = StorageManager(settings)
    manager.initialize()
    planner_store = manager.get_sqlite_store("planner")

    assert planner_store.get_metadata("agent_name") == "planner"
    assert planner_store.get_metadata("db_schema_version") == "1"
