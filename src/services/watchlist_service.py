"""
觀察清單服務，用於管理使用者追蹤的股票。

根據 service_contracts.md 第 1 節實作 CRUD 操作。
"""

from typing import List, Optional
import sqlite3
from datetime import datetime
import yfinance as yf

from src.database.db import get_db_connection
from src.models.watchlist import WatchlistEntry


def add_symbol(symbol: str, category: Optional[str] = None) -> WatchlistEntry:
    """
    驗證後將新股票新增至觀察清單。

    Args:
        symbol: 股票代碼 (例如 "NVDA")
        category: 可選分類 (例如 "Tech", "Core")

    Returns:
        WatchlistEntry: 新增的觀察清單項目

    Raises:
        ValueError: 如果股票代碼無效 (yfinance 找不到)
        sqlite3.IntegrityError: 如果股票代碼已存在 (UNIQUE 約束)

    Preconditions:
        - 資料庫已初始化並包含 watchlist 資料表
        - symbol 非空

    Postconditions:
        - 新資料列插入 watchlist 資料表
        - 股票立即顯示在 UI 側邊欄
    """
    # 根據驗證規則轉換為大寫
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("股票代碼不能為空")

    # 透過 yfinance 驗證股票代碼
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # 檢查股票代碼是否有效 (有數據)
    if not info or (info.get('regularMarketPrice') is None and info.get('symbol') is None):
        raise ValueError(f"無效的股票代碼: {symbol}")

    # 插入資料庫
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO watchlist (symbol, category)
        VALUES (?, ?)
        """,
        (symbol, category)
    )
    conn.commit()

    # 檢索插入的資料列
    row_id = cursor.lastrowid
    cursor = conn.execute(
        "SELECT * FROM watchlist WHERE id = ?",
        (row_id,)
    )
    row = cursor.fetchone()

    # 轉換為 WatchlistEntry
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
    從觀察清單中移除股票。

    Args:
        symbol: 要移除的股票代碼

    Returns:
        bool: 若刪除成功回傳 True，若找不到股票回傳 False

    Errors:
        - None (優雅地處理遺失的股票)

    Postconditions:
        - 資料列從 watchlist 資料表中刪除
        - 股票從 UI 側邊欄移除
    """
    symbol = symbol.strip().upper()

    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM watchlist WHERE symbol = ?",
        (symbol,)
    )
    conn.commit()

    # 檢查是否有資料列被刪除
    return cursor.rowcount > 0


def get_all_symbols() -> List[WatchlistEntry]:
    """
    檢索觀察清單中的所有股票。

    Returns:
        List[WatchlistEntry]: 依 added_at DESC 排序 (最新的在先)

    Errors:
        - sqlite3.Error: 資料庫連線失敗

    Postconditions: None (唯讀)
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
    依分類篩選觀察清單 (P4 使用者故事)。

    Args:
        category: 例如 "Tech", "Core"

    Returns:
        List[WatchlistEntry]: 符合分類的股票

    Errors: None

    Postconditions: None (唯讀)
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
