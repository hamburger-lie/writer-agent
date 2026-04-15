"""Centralized configuration and validation helpers."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


AGENT_NAMES = (
    "planner",
    "researcher",
    "writer",
    "polisher",
    "reviewer",
    "librarian",
)

SUPPORTED_SEARCH_ENGINES = ("serper", "bing", "google", "firecrawl")


class ValidationSeverity(StrEnum):
    """Severity levels used by configuration validation reports."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationItem(BaseModel):
    """One validation message for a configuration field."""

    field: str
    severity: ValidationSeverity
    message: str


class ValidationReport(BaseModel):
    """Collection of configuration validation messages."""

    items: list[ValidationItem] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(item.severity == ValidationSeverity.ERROR for item in self.items)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    search_engine: str | None = Field(default=None, alias="SEARCH_ENGINE")
    search_api_key: str | None = Field(default=None, alias="SEARCH_API_KEY")
    firecrawl_api_key: str | None = Field(default=None, alias="FIRECRAWL_API_KEY")
    whitepaper_api_url: str | None = Field(default=None, alias="WHITEPAPER_API_URL")
    data_dir_raw: str = Field(default="./data", alias="DATA_DIR")
    llm_timeout_seconds: int = Field(default=120, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")
    max_research_urls: int = Field(default=10, alias="MAX_RESEARCH_URLS")
    max_scrape_concurrent: int = Field(default=3, alias="MAX_SCRAPE_CONCURRENT")

    @property
    def project_root(self) -> Path:
        """Resolve the active project root from the current working directory."""

        return Path.cwd()

    @property
    def data_dir(self) -> Path:
        """Return the normalized runtime data directory."""

        raw = Path(self.data_dir_raw)
        return raw if raw.is_absolute() else (self.project_root / raw).resolve()

    def validate(self) -> ValidationReport:
        """Validate semantic configuration constraints used by CLI commands."""

        items: list[ValidationItem] = []

        if self.deepseek_api_key:
            items.append(
                ValidationItem(
                    field="DEEPSEEK_API_KEY",
                    severity=ValidationSeverity.INFO,
                    message="Configured.",
                )
            )
        else:
            items.append(
                ValidationItem(
                    field="DEEPSEEK_API_KEY",
                    severity=ValidationSeverity.ERROR,
                    message="Required for initialization and LLM-backed features.",
                )
            )

        if self.search_engine:
            if self.search_engine not in SUPPORTED_SEARCH_ENGINES:
                items.append(
                    ValidationItem(
                        field="SEARCH_ENGINE",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            "Unsupported search engine. Expected one of: "
                            + ", ".join(SUPPORTED_SEARCH_ENGINES)
                        ),
                    )
                )
            elif self.search_engine == "firecrawl":
                if self.firecrawl_api_key:
                    items.append(
                        ValidationItem(
                            field="FIRECRAWL_API_KEY",
                            severity=ValidationSeverity.INFO,
                            message="Configured for firecrawl.",
                        )
                    )
                else:
                    items.append(
                        ValidationItem(
                            field="FIRECRAWL_API_KEY",
                            severity=ValidationSeverity.ERROR,
                            message="Required when SEARCH_ENGINE is set to firecrawl.",
                        )
                    )
            elif self.search_api_key:
                items.append(
                    ValidationItem(
                        field="SEARCH_API_KEY",
                        severity=ValidationSeverity.INFO,
                        message=f"Configured for {self.search_engine}.",
                    )
                )
            else:
                items.append(
                    ValidationItem(
                        field="SEARCH_API_KEY",
                        severity=ValidationSeverity.ERROR,
                        message="Required when SEARCH_ENGINE is set.",
                    )
                )
        else:
            items.append(
                ValidationItem(
                    field="SEARCH_ENGINE",
                    severity=ValidationSeverity.WARNING,
                    message="Research integrations are disabled until a search engine is configured.",
                )
            )

        if self.whitepaper_api_url:
            items.append(
                ValidationItem(
                    field="WHITEPAPER_API_URL",
                    severity=ValidationSeverity.INFO,
                    message="Configured.",
                )
            )
        else:
            items.append(
                ValidationItem(
                    field="WHITEPAPER_API_URL",
                    severity=ValidationSeverity.WARNING,
                    message="Optional publishing integration is not configured.",
                )
            )

        return ValidationReport(items=items)


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    return Settings()


def get_settings(*, clear_cache: bool = False) -> Settings:
    """Return cached runtime settings, optionally clearing the cache first."""

    if clear_cache:
        _load_settings.cache_clear()
    return _load_settings()
