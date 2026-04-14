"""Base agent abstraction shared by all role-specific agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from writing_agent.config import Settings
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.sqlite_store import SQLiteStore
from writing_agent.storage.vector_store import DeferredVectorStore, VectorStoreNotReadyError


class BaseAgent(ABC):
    """Common dependencies and helper methods shared by all agents."""

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

    def load_rules(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.sqlite_store.list_active_rules()]

    def load_relevant_memory(self, query_text: str, n_results: int = 5) -> list[str]:
        try:
            result = self.vector_store.query(query_text, n_results=n_results)
        except VectorStoreNotReadyError:
            return []
        return result.documents

    def record_task_history(
        self,
        task_id: str,
        task_type: str,
        status: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
    ) -> int:
        return self.sqlite_store.add_task_history(
            task_id=task_id,
            task_type=task_type,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
        )

    def record_reflection(self, reflection_text: str, task_id: str | None = None) -> int:
        return self.sqlite_store.add_reflection(reflection_text=reflection_text, task_id=task_id)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent-specific task."""
