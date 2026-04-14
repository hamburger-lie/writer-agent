"""SQLite schema definitions shared by every agent database."""

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

CREATE_TASK_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT NOT NULL,
    duration_ms INTEGER,
    token_usage_json TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_REFLECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    reflection_text TEXT NOT NULL,
    trigger_context TEXT,
    times_seen INTEGER NOT NULL DEFAULT 1,
    promoted_to_rule INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
)
"""

CREATE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
