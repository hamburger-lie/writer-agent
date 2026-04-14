from __future__ import annotations

from pathlib import Path

import pytest

from writing_agent.storage.vector_store import DeferredVectorStore, VectorStoreNotReadyError


def test_vector_store_placeholder_raises_not_ready(tmp_path: Path) -> None:
    store = DeferredVectorStore(tmp_path / "chroma", collection_name="planner_knowledge")
    store.initialize()

    with pytest.raises(VectorStoreNotReadyError):
        store.query("market trend", n_results=5)
