"""
Watchlist service for managing user-tracked symbols.

Implements CRUD operations per service_contracts.md Section 1.
"""

from typing import List, Optional
import sqlite3
from datetime import datetime
import yfinance as yf

from src.database.db import get_db_connection
from src.models.watchlist import WatchlistEntry


def add_symbol(symbol: str, category: Optional[str] = None) -> WatchlistEntry:
    """
    Add a new symbol to the watchlist after validation.

    Args:
        symbol: Ticker symbol (e.g., "NVDA")
        category: Optional category (e.g., "Tech", "Core")

    Returns:
        WatchlistEntry: The newly added watchlist entry

    Raises:
        ValueError: If symbol is invalid (not found via yfinance)
        sqlite3.IntegrityError: If symbol already exists (UNIQUE constraint)

    Preconditions:
    - Database initialized with watchlist table
    - symbol is non-empty

    Postconditions:
    - New row inserted in watchlist table
    - Symbol appears in UI sidebar immediately
    """
    # Uppercase symbol per validation rules
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Symbol cannot be empty")

    # Validate symbol via yfinance
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # Check if symbol is valid (has data)
    if not info or (info.get('regularMarketPrice') is None and info.get('symbol') is None):
        raise ValueError(f"Invalid symbol: {symbol}")

    # Insert into database
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO watchlist (symbol, category)
        VALUES (?, ?)
        """,
        (symbol, category)
    )
    conn.commit()

    # Retrieve the inserted row
    row_id = cursor.lastrowid
    cursor = conn.execute(
        "SELECT * FROM watchlist WHERE id = ?",
        (row_id,)
    )
    row = cursor.fetchone()

    # Convert to WatchlistEntry
    return WatchlistEntry(
        id=row['id'],
        symbol=row['symbol'],
        added_at=datetime.fromisoformat(row['added_at']),
        category=row['category'],
        notes=row['notes'],
        enabled=bool(row['enabled'])
    )


def remove_symbol(symbol: str) -> bool:
    """
    Remove a symbol from the watchlist.

    Args:
        symbol: Ticker to remove

    Returns:
        bool: True if deleted, False if symbol not found

    Errors:
    - None (gracefully handles missing symbols)

    Postconditions:
    - Row deleted from watchlist table
    - Symbol removed from UI sidebar
    """
    symbol = symbol.strip().upper()

    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM watchlist WHERE symbol = ?",
        (symbol,)
    )
    conn.commit()

    # Check if any rows were deleted
    return cursor.rowcount > 0


def get_all_symbols() -> List[WatchlistEntry]:
    """
    Retrieve all symbols in the watchlist.

    Returns:
        List[WatchlistEntry]: Ordered by added_at DESC (newest first)

    Errors:
    - sqlite3.Error: Database connection failure

    Postconditions: None (read-only)
    """
    conn = get_db_connection()
    cursor = conn.execute(
        """
        SELECT * FROM watchlist
        ORDER BY added_at DESC
        """
    )

    results = []
    for row in cursor.fetchall():
        entry = WatchlistEntry(
            id=row['id'],
            symbol=row['symbol'],
            added_at=datetime.fromisoformat(row['added_at']),
            category=row['category'],
            notes=row['notes'],
            enabled=bool(row['enabled'])
        )
        results.append(entry)

    return results


def get_symbols_by_category(category: str) -> List[WatchlistEntry]:
    """
    Filter watchlist by category (P4 user story).

    Args:
        category: e.g., "Tech", "Core"

    Returns:
        List[WatchlistEntry]: Symbols with matching category

    Errors: None

    Postconditions: None (read-only)
    """
    conn = get_db_connection()
    cursor = conn.execute(
        """
        SELECT * FROM watchlist
        WHERE category = ?
        ORDER BY added_at DESC
        """,
        (category,)
    )

    results = []
    for row in cursor.fetchall():
        entry = WatchlistEntry(
            id=row['id'],
            symbol=row['symbol'],
            added_at=datetime.fromisoformat(row['added_at']),
            category=row['category'],
            notes=row['notes'],
            enabled=bool(row['enabled'])
        )
        results.append(entry)

    return results
