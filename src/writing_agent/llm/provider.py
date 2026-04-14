"""LLM provider abstractions for DeepSeek-backed interactions."""

from __future__ import annotations

import json
from typing import Any

import httpx

from writing_agent.config import Settings
from writing_agent.llm.models import DEEPSEEK_CHAT, REASONING_MODELS


class LLMError(RuntimeError):
    """Base exception for LLM-related failures."""


class LLMConfigurationError(LLMError):
    """Raised when required LLM configuration is missing."""


class LLMTransportError(LLMError):
    """Raised when the upstream HTTP request fails."""


class LLMResponseParseError(LLMError):
    """Raised when the model response shape is invalid."""


class LLMProvider:
    """Wrapper around DeepSeek chat completion requests."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_config(self) -> None:
        if not self.settings.deepseek_api_key:
            raise LLMConfigurationError("DEEPSEEK_API_KEY is required before using the LLM provider.")

    def build_request_payload(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        chosen_model = model or DEEPSEEK_CHAT
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
        }
        if temperature is not None and chosen_model not in REASONING_MODELS:
            payload["temperature"] = temperature
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.validate_config()
        payload = self.build_request_payload(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )

        try:
            with httpx.Client(
                base_url=self.settings.deepseek_base_url,
                timeout=self.settings.llm_timeout_seconds,
            ) as client:
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMTransportError(str(exc)) from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseParseError("Unexpected DeepSeek response shape.") from exc

    def generate_json(
        self, prompt: str, system_prompt: str | None = None, model: str | None = None
    ) -> dict[str, Any]:
        raw = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseParseError("Model response was not valid JSON.") from exc
