# Stage 2 Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Stage 2 infrastructure foundation so `writing-agent` can load and validate configuration, initialize per-agent SQLite storage, expose stable vector and LLM interfaces, and provide CLI commands for initialization and config inspection.

**Architecture:** Configuration, filesystem layout, and SQLite storage become fully operational first. Vector storage and LLM access are introduced as typed service boundaries with explicit deferred-backend behavior, so later stages can plug in real backends without changing callers.

**Tech Stack:** Python 3.11, Typer, Rich, sqlite3, pydantic-settings, pytest

---

**Workspace note:** This workspace is not currently a Git repository. Replace the usual commit step with a checkpoint step that records touched files and the verification command.

### Task 1: Implement Typed Settings and Validation

**Files:**
- Modify: `src/writing_agent/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

import pytest

from writing_agent.config import ValidationSeverity, get_settings


def test_settings_resolve_data_dir_relative_to_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DATA_DIR", "./runtime-data")

    settings = get_settings(clear_cache=True)

    assert settings.data_dir == tmp_path / "runtime-data"


def test_validation_requires_deepseek_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    settings = get_settings(clear_cache=True)
    report = settings.validate()

    assert any(item.severity == ValidationSeverity.ERROR for item in report.items)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL because `writing_agent.config` does not yet expose typed settings or validation reporting.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AGENT_NAMES = ("planner", "researcher", "writer", "polisher", "reviewer", "librarian")


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationItem(BaseModel):
    field: str
    severity: ValidationSeverity
    message: str


class ValidationReport(BaseModel):
    items: list[ValidationItem] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(item.severity == ValidationSeverity.ERROR for item in self.items)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    search_engine: str | None = Field(default=None, alias="SEARCH_ENGINE")
    search_api_key: str | None = Field(default=None, alias="SEARCH_API_KEY")
    whitepaper_api_url: str | None = Field(default=None, alias="WHITEPAPER_API_URL")
    data_dir_raw: str = Field(default="./data", alias="DATA_DIR")

    @property
    def data_dir(self) -> Path:
        raw = Path(self.data_dir_raw)
        return raw if raw.is_absolute() else (Path.cwd() / raw).resolve()

    def validate(self) -> ValidationReport:
        items: list[ValidationItem] = []
        if self.deepseek_api_key:
            items.append(ValidationItem(field="DEEPSEEK_API_KEY", severity=ValidationSeverity.INFO, message="Configured"))
        else:
            items.append(ValidationItem(field="DEEPSEEK_API_KEY", severity=ValidationSeverity.ERROR, message="Required for initialization"))
        return ValidationReport(items=items)


@lru_cache(maxsize=1)
def get_settings(clear_cache: bool = False) -> Settings:
    if clear_cache:
        get_settings.cache_clear()
    return Settings()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS with settings loading and validation behavior covered.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_config.py -v`

### Task 2: Implement SQLite Schema and Store Operations

**Files:**
- Modify: `src/writing_agent/storage/schema.py`
- Modify: `src/writing_agent/storage/sqlite_store.py`
- Test: `tests/test_storage/test_sqlite_store.py`

- [ ] **Step 1: Write the failing tests**

```python
import sqlite3
from pathlib import Path

from writing_agent.storage.sqlite_store import SQLiteStore


def test_initialize_schema_creates_all_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "planner.db")
    store.initialize_schema()

    with sqlite3.connect(tmp_path / "planner.db") as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        }

    assert {"rules", "task_history", "reflections", "metadata"} <= tables
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_storage/test_sqlite_store.py -v`
Expected: FAIL because schema SQL and store methods are not implemented.

- [ ] **Step 3: Write the minimal implementation**

```python
SCHEMA_VERSION = "1"

CREATE_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    category TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
)
"""
```

```python
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from writing_agent.storage import schema


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def initialize_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(schema.CREATE_RULES_TABLE)
            conn.execute(schema.CREATE_TASK_HISTORY_TABLE)
            conn.execute(schema.CREATE_REFLECTIONS_TABLE)
            conn.execute(schema.CREATE_METADATA_TABLE)
            conn.commit()

    def upsert_metadata(self, key: str, value: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_storage/test_sqlite_store.py -v`
Expected: PASS with schema creation and metadata persistence working.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_storage/test_sqlite_store.py -v`

### Task 3: Implement the Storage Manager and Deferred Vector Store

**Files:**
- Modify: `src/writing_agent/storage/manager.py`
- Modify: `src/writing_agent/storage/vector_store.py`
- Test: `tests/test_storage/test_manager.py`
- Test: `tests/test_storage/test_vector_store.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

import pytest

from writing_agent.config import get_settings
from writing_agent.storage.manager import StorageManager
from writing_agent.storage.vector_store import VectorStoreNotReadyError


def test_storage_manager_initializes_all_agent_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    settings = get_settings(clear_cache=True)

    manager = StorageManager(settings)
    result = manager.initialize()

    assert len(result.initialized_agents) == 6
    assert (settings.data_dir / "agents" / "planner" / "planner.db").exists()
    assert (settings.data_dir / "shared" / "chroma").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py -v`
Expected: FAIL because the storage manager does not yet create the runtime layout and the vector backend boundary does not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from writing_agent.config import AGENT_NAMES, Settings
from writing_agent.storage.schema import SCHEMA_VERSION
from writing_agent.storage.sqlite_store import SQLiteStore
from writing_agent.storage.vector_store import DeferredVectorStore


@dataclass(slots=True)
class InitializationResult:
    initialized_agents: list[str]


class StorageManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_sqlite_store(self, agent_name: str) -> SQLiteStore:
        return SQLiteStore(self.settings.data_dir / "agents" / agent_name / f"{agent_name}.db")

    def get_vector_store(self, agent_name: str) -> DeferredVectorStore:
        return DeferredVectorStore(
            self.settings.data_dir / "agents" / agent_name / "chroma",
            collection_name=f"{agent_name}_knowledge",
        )

    def initialize(self) -> InitializationResult:
        (self.settings.data_dir / "shared" / "chroma").mkdir(parents=True, exist_ok=True)
        (self.settings.data_dir / "tasks").mkdir(parents=True, exist_ok=True)
        (self.settings.data_dir / "exports").mkdir(parents=True, exist_ok=True)
        initialized_at = datetime.now(UTC).isoformat()
        initialized_agents: list[str] = []
        for agent_name in AGENT_NAMES:
            agent_dir = self.settings.data_dir / "agents" / agent_name
            (agent_dir / "chroma").mkdir(parents=True, exist_ok=True)
            store = self.get_sqlite_store(agent_name)
            store.initialize_schema()
            store.upsert_metadata("agent_name", agent_name)
            store.upsert_metadata("db_schema_version", SCHEMA_VERSION)
            store.upsert_metadata("initialized_at", initialized_at)
            initialized_agents.append(agent_name)
        return InitializationResult(initialized_agents=initialized_agents)
```

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class VectorStoreNotReadyError(RuntimeError):
    """Raised when the vector backend has not been wired to a real implementation yet."""


@dataclass(slots=True)
class QueryResult:
    ids: list[str]
    documents: list[str]
    metadatas: list[dict[str, str]]


class DeferredVectorStore:
    def __init__(self, root_dir: Path, collection_name: str) -> None:
        self.root_dir = root_dir
        self.collection_name = collection_name

    def initialize(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def query(self, query_text: str, n_results: int = 5) -> QueryResult:
        raise VectorStoreNotReadyError("Vector search is not enabled in Stage 2.")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py -v`
Expected: PASS with runtime layout creation and deferred vector behavior covered.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py -v`

### Task 4: Implement Model Constants, LLM Provider, and BaseAgent

**Files:**
- Modify: `src/writing_agent/llm/models.py`
- Modify: `src/writing_agent/llm/provider.py`
- Modify: `src/writing_agent/agents/base.py`
- Test: `tests/test_llm/test_provider.py`

- [ ] **Step 1: Write the failing tests**

```python
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
        model="deepseek-reasoner",
        temperature=0.2,
    )

    assert "temperature" not in payload
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_llm/test_provider.py -v`
Expected: FAIL because the provider does not yet expose config validation or request payload normalization.

- [ ] **Step 3: Write the minimal implementation**

```python
DEEPSEEK_CHAT = "deepseek-chat"
DEEPSEEK_REASONER = "deepseek-reasoner"
REASONING_MODELS = {DEEPSEEK_REASONER}
```

```python
from __future__ import annotations

from typing import Any

from writing_agent.config import Settings
from writing_agent.llm.models import DEEPSEEK_CHAT, REASONING_MODELS


class LLMConfigurationError(RuntimeError):
    """Raised when required LLM configuration is missing."""


class LLMProvider:
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
    ) -> dict[str, Any]:
        chosen_model = model or DEEPSEEK_CHAT
        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
        if temperature is not None and chosen_model not in REASONING_MODELS:
            payload["temperature"] = temperature
        return payload
```

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from writing_agent.config import Settings
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.sqlite_store import SQLiteStore
from writing_agent.storage.vector_store import DeferredVectorStore, VectorStoreNotReadyError


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        role: str,
        settings: Settings,
        sqlite_store: SQLiteStore,
        vector_store: DeferredVectorStore,
        llm_provider: LLMProvider,
    ) -> None:
        self.name = name
        self.role = role
        self.settings = settings
        self.sqlite_store = sqlite_store
        self.vector_store = vector_store
        self.llm_provider = llm_provider

    def load_relevant_memory(self, query_text: str, n_results: int = 5) -> list[str]:
        try:
            result = self.vector_store.query(query_text, n_results=n_results)
        except VectorStoreNotReadyError:
            return []
        return result.documents

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_llm/test_provider.py -v`
Expected: PASS with config validation and request payload normalization covered.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_llm/test_provider.py -v`

### Task 5: Wire the CLI Commands and Run Full Stage 2 Verification

**Files:**
- Modify: `src/writing_agent/cli/app.py`
- Modify: `src/writing_agent/main.py`
- Create: `src/writing_agent/cli/commands/init.py`
- Create: `src/writing_agent/cli/commands/config.py`
- Test: `tests/test_cli/test_init_command.py`
- Test: `tests/test_cli/test_config_command.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app


def test_init_command_creates_runtime_layout(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / "data" / "agents" / "planner" / "planner.db").exists()
    assert "Initialized 6 agent databases" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cli/test_init_command.py tests/test_cli/test_config_command.py -v`
Expected: FAIL because the CLI command modules are not wired and the application has no init/config behavior yet.

- [ ] **Step 3: Write the minimal implementation**

```python
import typer

from writing_agent.cli.commands.config import app as config_app
from writing_agent.cli.commands.init import init_command

app = typer.Typer(help="Multi-agent writing system CLI.")
app.command("init")(init_command)
app.add_typer(config_app, name="config")
```

```python
from __future__ import annotations

import typer
from rich.console import Console

from writing_agent.config import ValidationSeverity, get_settings
from writing_agent.storage.manager import StorageManager

console = Console()


def init_command() -> None:
    settings = get_settings(clear_cache=True)
    report = settings.validate()
    if report.has_errors:
        for item in report.items:
            console.print(f"{item.severity.upper()} {item.field}: {item.message}")
        raise typer.Exit(code=1)

    result = StorageManager(settings).initialize()
    console.print(f"Initialized {len(result.initialized_agents)} agent databases")

    for item in report.items:
        if item.severity == ValidationSeverity.WARNING:
            console.print(f"WARNING {item.field}: {item.message}")
```

```python
from __future__ import annotations

import typer
from rich.console import Console

from writing_agent.config import get_settings

app = typer.Typer(help="Inspect resolved configuration.")
console = Console()


@app.command("show")
def show_config() -> None:
    settings = get_settings(clear_cache=True)
    report = settings.validate()
    console.print(f"data_dir={settings.data_dir}")
    console.print(f"search_engine={settings.search_engine or '<disabled>'}")
    for item in report.items:
        console.print(f"{item.severity.upper()} {item.field}: {item.message}")
```

- [ ] **Step 4: Run the full verification**

Run: `pytest tests/test_config.py tests/test_storage/test_sqlite_store.py tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py tests/test_llm/test_provider.py tests/test_cli/test_init_command.py tests/test_cli/test_config_command.py -v`
Expected: PASS with Stage 2 behavior covered end-to-end.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_config.py tests/test_storage/test_sqlite_store.py tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py tests/test_llm/test_provider.py tests/test_cli/test_init_command.py tests/test_cli/test_config_command.py -v`
