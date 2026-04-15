"""Storage manager for initializing and locating per-agent storage resources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from writing_agent.config import AGENT_NAMES, Settings
from writing_agent.storage.schema import SCHEMA_VERSION
from writing_agent.storage.shared_knowledge_store import SharedKnowledgeStore
from writing_agent.storage.sqlite_store import SQLiteStore
from writing_agent.storage.vector_store import DeferredVectorStore


@dataclass(slots=True)
class AgentPaths:
    """Concrete filesystem paths for a single agent."""

    root: Path
    db_path: Path
    chroma_dir: Path


@dataclass(slots=True)
class InitializationResult:
    """Summary of the resources initialized by the storage manager."""

    initialized_agents: list[str]
    created_directories: list[Path]


class StorageManager:
    """Factory and bootstrapper for per-agent storage."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_agent_paths(self, agent_name: str) -> AgentPaths:
        agent_root = self.settings.data_dir / "agents" / agent_name
        return AgentPaths(
            root=agent_root,
            db_path=agent_root / f"{agent_name}.db",
            chroma_dir=agent_root / "chroma",
        )

    def get_sqlite_store(self, agent_name: str) -> SQLiteStore:
        return SQLiteStore(self.get_agent_paths(agent_name).db_path)

    def get_shared_library_path(self) -> Path:
        return self.settings.data_dir / "shared" / "library.db"

    def get_shared_knowledge_store(self) -> SharedKnowledgeStore:
        return SharedKnowledgeStore(self.get_shared_library_path())

    def get_vector_store(self, agent_name: str) -> DeferredVectorStore:
        return DeferredVectorStore(
            self.get_agent_paths(agent_name).chroma_dir,
            collection_name=f"{agent_name}_knowledge",
        )

    def initialize(self) -> InitializationResult:
        created_directories: list[Path] = []
        for path in (
            self.settings.data_dir,
            self.settings.data_dir / "agents",
            self.settings.data_dir / "shared" / "chroma",
            self.settings.data_dir / "shared",
            self.settings.data_dir / "tasks",
            self.settings.data_dir / "exports",
        ):
            path.mkdir(parents=True, exist_ok=True)
            created_directories.append(path)

        initialized_agents: list[str] = []
        initialized_at = datetime.now(UTC).isoformat()

        for agent_name in AGENT_NAMES:
            paths = self.get_agent_paths(agent_name)
            paths.root.mkdir(parents=True, exist_ok=True)
            paths.chroma_dir.mkdir(parents=True, exist_ok=True)
            created_directories.extend([paths.root, paths.chroma_dir])

            store = self.get_sqlite_store(agent_name)
            store.initialize_schema()
            store.upsert_metadata("agent_name", agent_name)
            store.upsert_metadata("agent_role", agent_name)
            store.upsert_metadata("db_schema_version", SCHEMA_VERSION)
            store.upsert_metadata("initialized_at", initialized_at)

            self.get_vector_store(agent_name).initialize()
            initialized_agents.append(agent_name)

        self.get_shared_knowledge_store().initialize_schema()

        return InitializationResult(
            initialized_agents=initialized_agents,
            created_directories=created_directories,
        )
