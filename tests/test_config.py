from __future__ import annotations

from pathlib import Path

import pytest

from writing_agent.config import ValidationSeverity, get_settings


def test_settings_resolve_data_dir_relative_to_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATA_DIR", "./runtime-data")

    settings = get_settings(clear_cache=True)

    assert settings.data_dir == tmp_path / "runtime-data"


def test_validation_requires_deepseek_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WHITEPAPER_API_URL", raising=False)

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    assert any(
        item.severity == ValidationSeverity.ERROR and item.field == "DEEPSEEK_API_KEY"
        for item in report.items
    )


def test_validation_warns_for_missing_optional_whitepaper_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("SEARCH_ENGINE", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("WHITEPAPER_API_URL", raising=False)

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    assert any(
        item.severity == ValidationSeverity.WARNING and item.field == "WHITEPAPER_API_URL"
        for item in report.items
    )


def test_validation_requires_search_api_key_when_engine_is_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SEARCH_ENGINE", "serper")
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    assert any(
        item.severity == ValidationSeverity.ERROR and item.field == "SEARCH_API_KEY"
        for item in report.items
    )
