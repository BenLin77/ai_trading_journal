"""
Unit tests for watchlist service.

TDD workflow: These tests are written FIRST before implementation.
Per Constitution Principle V (Test-First for Financial Logic).
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name

    os.environ['DB_PATH'] = db_path

    # Initialize database
    from src.database.db import initialize_db
    initialize_db()

    yield db_path

    # Cleanup
    if Path(db_path).exists():
        Path(db_path).unlink()

    # Clear Streamlit cache
    try:
        import streamlit as st
        st.cache_resource.clear()
    except:
        pass


def test_add_symbol_success(temp_db):
    """
    Test T020: add_symbol() success case.

    Given a valid symbol,
    When add_symbol is called,
    Then it returns WatchlistEntry with correct data.
    """
    from src.services.watchlist_service import add_symbol
    from src.models.watchlist import WatchlistEntry

    # Mock yfinance to avoid network calls
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'NVDA', 'shortName': 'NVIDIA Corporation'}

        result = add_symbol("nvda")  # Lowercase to test uppercase conversion

        assert isinstance(result, WatchlistEntry), "Should return WatchlistEntry"
        assert result.symbol == "NVDA", "Symbol should be uppercased"
        assert result.enabled is True, "Enabled should default to True"
        assert result.id > 0, "Should have database ID"
        assert isinstance(result.added_at, datetime), "Should have timestamp"


def test_add_symbol_with_category(temp_db):
    """Test add_symbol() with category parameter."""
    from src.services.watchlist_service import add_symbol

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'AMD', 'shortName': 'AMD'}

        result = add_symbol("AMD", category="Tech")

        assert result.symbol == "AMD"
        assert result.category == "Tech", "Category should be stored"


def test_add_symbol_duplicate_rejection(temp_db):
    """
    Test T021: add_symbol() duplicate rejection.

    Given a symbol already in watchlist,
    When add_symbol is called with same symbol,
    Then it raises IntegrityError.
    """
    from src.services.watchlist_service import add_symbol

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'NVDA', 'shortName': 'NVIDIA'}

        # Add first time - should succeed
        add_symbol("NVDA")

        # Add second time - should raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            add_symbol("NVDA")


def test_add_symbol_invalid_symbol_rejection(temp_db):
    """
    Test T022: add_symbol() invalid symbol rejection.

    Given an invalid ticker symbol,
    When add_symbol is called,
    Then it raises ValueError.
    """
    from src.services.watchlist_service import add_symbol

    # Mock yfinance to return empty/invalid info
    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {}  # Empty info = invalid symbol

        with pytest.raises(ValueError, match="無效的股票代碼"):
            add_symbol("INVALID123")


def test_remove_symbol_success(temp_db):
    """
    Test T023: remove_symbol() returns True when symbol exists.

    Given a symbol in watchlist,
    When remove_symbol is called,
    Then it returns True and symbol is deleted.
    """
    from src.services.watchlist_service import add_symbol, remove_symbol, get_all_symbols

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'AMD', 'shortName': 'AMD'}

        # Add symbol first
        add_symbol("AMD")
        assert len(get_all_symbols()) == 1, "Symbol should be added"

        # Remove symbol
        result = remove_symbol("AMD")

        assert result is True, "Should return True for successful deletion"
        assert len(get_all_symbols()) == 0, "Symbol should be removed"


def test_remove_symbol_not_found(temp_db):
    """
    Test T023: remove_symbol() returns False when symbol not found.

    Given an empty watchlist,
    When remove_symbol is called,
    Then it returns False (gracefully handles missing symbols).
    """
    from src.services.watchlist_service import remove_symbol

    result = remove_symbol("NONEXISTENT")

    assert result is False, "Should return False when symbol not found"


def test_get_all_symbols_ordered(temp_db):
    """
    Test T024: get_all_symbols() returns list ordered by added_at DESC.

    Given multiple symbols in watchlist,
    When get_all_symbols is called,
    Then it returns list ordered by most recent first.
    """
    from src.services.watchlist_service import add_symbol, get_all_symbols
    import time

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {'symbol': 'TEST', 'shortName': 'Test'}

        # Add symbols with 1-second delay to ensure different timestamps
        # (SQLite DATETIME has second-level precision)
        add_symbol("AAPL")
        time.sleep(1.1)
        add_symbol("NVDA")
        time.sleep(1.1)
        add_symbol("AMD")

        results = get_all_symbols()

        assert len(results) == 3, "Should return all 3 symbols"
        assert results[0].symbol == "AMD", "Most recent symbol should be first"
        assert results[1].symbol == "NVDA", "Second most recent should be second"
        assert results[2].symbol == "AAPL", "Oldest symbol should be last"


def test_get_all_symbols_empty(temp_db):
    """Test get_all_symbols() with empty watchlist."""
    from src.services.watchlist_service import get_all_symbols

    results = get_all_symbols()

    assert results == [], "Should return empty list for empty watchlist"
