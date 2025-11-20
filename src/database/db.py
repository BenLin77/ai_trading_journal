"""
Database management module for AI Trading Journal.

Provides singleton connection management and schema initialization
per Constitution Principle I (Privacy-First) and PERF-006.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import streamlit as st
import os


# SQL Schema Definition
CREATE_WATCHLIST_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    enabled BOOLEAN DEFAULT 1
);
"""

CREATE_WATCHLIST_CATEGORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_watchlist_category ON watchlist(category);
"""

CREATE_WATCHLIST_ENABLED_INDEX = """
CREATE INDEX IF NOT EXISTS idx_watchlist_enabled ON watchlist(enabled);
"""


@st.cache_resource
def get_db_connection() -> sqlite3.Connection:
    """
    Get singleton database connection (cached as resource).

    Returns:
        sqlite3.Connection: Configured with WAL mode, row_factory

    Configuration per research.md Section 4:
    - WAL mode: Prevents database corruption
    - row_factory: Dict-like access to rows
    - check_same_thread: Allow Streamlit's threading model
    """
    db_path = os.getenv("DB_PATH", "trading_journal.db")

    conn = sqlite3.connect(db_path, check_same_thread=False)

    # Enable WAL mode for better concurrency and corruption prevention
    conn.execute("PRAGMA journal_mode=WAL;")

    # Enable dict-like row access
    conn.row_factory = sqlite3.Row

    return conn


def initialize_db() -> None:
    """
    Create schema if not exists, run migrations.

    Called on app startup (in pages/6_GEX_Sentinel.py).
    Uses PRAGMA user_version for migration tracking.

    Raises:
        sqlite3.Error: Database connection or schema creation failure
    """
    conn = get_db_connection()

    # Check current schema version
    current_version = conn.execute("PRAGMA user_version;").fetchone()[0]

    if current_version == 0:
        # Initial schema creation
        conn.execute(CREATE_WATCHLIST_TABLE_SQL)
        conn.execute(CREATE_WATCHLIST_CATEGORY_INDEX)
        conn.execute(CREATE_WATCHLIST_ENABLED_INDEX)
        conn.execute("PRAGMA user_version = 1;")
        conn.commit()

    # Future migrations go here
    # if current_version == 1:
    #     conn.execute("ALTER TABLE watchlist ADD COLUMN new_field TEXT;")
    #     conn.execute("PRAGMA user_version = 2;")
    #     conn.commit()
