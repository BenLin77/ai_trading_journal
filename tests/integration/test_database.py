"""
Integration tests for database initialization and persistence.

Tests verify database schema and CRUD operations per contract requirements.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name

    # Set environment variable for test database
    os.environ['DB_PATH'] = db_path

    yield db_path

    # Cleanup
    if Path(db_path).exists():
        Path(db_path).unlink()

    # Clean up Streamlit cache to avoid singleton issues
    try:
        import streamlit as st
        st.cache_resource.clear()
    except:
        pass


def test_database_initialization(temp_db):
    """Test T017: Verify watchlist table exists with correct schema."""
    from src.database.db import initialize_db, get_db_connection

    # Initialize database
    initialize_db()

    # Get connection
    conn = get_db_connection()

    # Verify watchlist table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist';"
    )
    tables = cursor.fetchall()
    assert len(tables) == 1, "Watchlist table should exist"

    # Verify schema columns
    cursor = conn.execute("PRAGMA table_info(watchlist);")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type

    expected_columns = {
        'id': 'INTEGER',
        'symbol': 'TEXT',
        'added_at': 'DATETIME',
        'category': 'TEXT',
        'notes': 'TEXT',
        'enabled': 'BOOLEAN'
    }

    for col_name, col_type in expected_columns.items():
        assert col_name in columns, f"Column {col_name} should exist"
        assert columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

    # Verify UNIQUE constraint on symbol
    cursor = conn.execute("PRAGMA index_list(watchlist);")
    indexes = cursor.fetchall()
    assert any('unique' in str(idx).lower() or idx[2] == 1 for idx in indexes), \
        "Symbol should have UNIQUE constraint"

    # Verify indexes exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='watchlist';")
    index_names = [row[0] for row in cursor.fetchall()]
    assert any('category' in name for name in index_names), "Category index should exist"
    assert any('enabled' in name for name in index_names), "Enabled index should exist"


def test_database_persistence(temp_db):
    """Test T018: Verify insert/query/delete operations work."""
    from src.database.db import initialize_db, get_db_connection

    # Initialize database
    initialize_db()
    conn = get_db_connection()

    # Test INSERT
    cursor = conn.execute(
        "INSERT INTO watchlist (symbol, category) VALUES (?, ?);",
        ("NVDA", "Tech")
    )
    conn.commit()
    nvda_id = cursor.lastrowid
    assert nvda_id > 0, "Insert should return row ID"

    # Test SELECT
    cursor = conn.execute("SELECT * FROM watchlist WHERE symbol = ?;", ("NVDA",))
    row = cursor.fetchone()
    assert row is not None, "Should retrieve inserted row"
    assert row['symbol'] == "NVDA", "Symbol should match"
    assert row['category'] == "Tech", "Category should match"
    assert row['enabled'] == 1, "Enabled should default to 1"

    # Test UNIQUE constraint violation
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO watchlist (symbol, category) VALUES (?, ?);",
            ("NVDA", "Core")
        )

    # Test UPDATE
    conn.execute("UPDATE watchlist SET category = ? WHERE symbol = ?;", ("Core", "NVDA"))
    conn.commit()
    cursor = conn.execute("SELECT category FROM watchlist WHERE symbol = ?;", ("NVDA",))
    row = cursor.fetchone()
    assert row['category'] == "Core", "Update should change category"

    # Test DELETE
    conn.execute("DELETE FROM watchlist WHERE symbol = ?;", ("NVDA",))
    conn.commit()
    cursor = conn.execute("SELECT * FROM watchlist WHERE symbol = ?;", ("NVDA",))
    row = cursor.fetchone()
    assert row is None, "Delete should remove row"

    # Test persistence across connections (verify WAL mode works)
    conn.execute("INSERT INTO watchlist (symbol) VALUES (?);", ("AMD",))
    conn.commit()

    # Create new connection to same database
    conn2 = sqlite3.connect(temp_db, check_same_thread=False)
    cursor2 = conn2.execute("SELECT symbol FROM watchlist WHERE symbol = ?;", ("AMD",))
    row2 = cursor2.fetchone()
    assert row2 is not None, "Data should persist across connections"
    assert row2[0] == "AMD", "Symbol should match"
    conn2.close()
