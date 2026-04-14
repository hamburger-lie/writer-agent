from __future__ import annotations

import pytest

from writing_agent.config import Settings
from writing_agent.llm.provider import LLMConfigurationError, LLMProvider


def test_validate_config_rejects_missing_api_key() -> None:
    provider = LLMProvider(Settings(DEEPSEEK_API_KEY=None))

    with pytest.raises(LLMConfigurationError):
        provider.validate_config()


def test_reasoner_model_omits_temperature_argument() -> None:
    provider = LLMProvider(Settings(DEEPSEEK_API_KEY="test-key"))

    payload = provider.build_request_payload(
        prompt="Outline an article.",
        system_prompt="You are a planner.",
        model="deepseek-reasoner",
        temperature=0.2,
    )

    assert payload["model"] == "deepseek-reasoner"
    assert "temperature" not in payload


def test_chat_model_keeps_temperature_argument() -> None:
    provider = LLMProvider(Settings(DEEPSEEK_API_KEY="test-key"))

    payload = provider.build_request_payload(
        prompt="Draft an introduction.",
        model="deepseek-chat",
        temperature=0.7,
    )

    assert payload["temperature"] == 0.7
