"""Deferred vector store boundary used until a real backend is wired in."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class VectorStoreError(RuntimeError):
    """Base exception for vector store failures."""


class VectorStoreNotReadyError(VectorStoreError):
    """Raised when vector storage is not available in the current stage."""


@dataclass(slots=True)
class QueryResult:
    """Normalized query result shape for future vector backend implementations."""

    ids: list[str]
    documents: list[str]
    metadatas: list[dict[str, str]]


class DeferredVectorStore:
    """Placeholder vector store that preserves the future backend contract."""

    def __init__(self, root_dir: Path, collection_name: str) -> None:
        self.root_dir = root_dir
        self.collection_name = collection_name

    def initialize(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def add_documents(
        self, documents: list[str], metadatas: list[dict[str, str]] | None = None
    ) -> None:
        raise VectorStoreNotReadyError("Vector storage is not enabled in Stage 2.")

    def query(self, query_text: str, n_results: int = 5) -> QueryResult:
        raise VectorStoreNotReadyError("Vector search is not enabled in Stage 2.")

    def delete(self, ids: list[str]) -> None:
        raise VectorStoreNotReadyError("Vector deletion is not enabled in Stage 2.")
