"""
AI 交易日誌的資料庫管理模組。

根據憲法原則 I (隱私優先) 和 PERF-006 提供單例連線管理和架構初始化。
"""

import sqlite3
from pathlib import Path
from typing import Optional
import streamlit as st
import os


# SQL 架構定義
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
    獲取單例資料庫連線 (快取為資源)。

    Returns:
        sqlite3.Connection: 已配置 WAL 模式和 row_factory

    配置根據 research.md 第 4 節:
    - WAL 模式: 防止資料庫損壞
    - row_factory: 類似字典的資料列存取
    - check_same_thread: 允許 Streamlit 的執行緒模型
    """
    db_path = os.getenv("DB_PATH", "trading_journal.db")

    conn = sqlite3.connect(db_path, check_same_thread=False)

    # 啟用 WAL 模式以獲得更好的並發性和防止損壞
    conn.execute("PRAGMA journal_mode=WAL;")

    # 啟用類似字典的資料列存取
    conn.row_factory = sqlite3.Row

    return conn


def initialize_db() -> None:
    """
    如果不存在則建立架構，執行遷移。

    在應用程式啟動時呼叫 (在 pages/6_GEX_Sentinel.py 中)。
    使用 PRAGMA user_version 進行遷移追蹤。

    Raises:
        sqlite3.Error: 資料庫連線或架構建立失敗
    """
    conn = get_db_connection()

    # 檢查目前架構版本
    current_version = conn.execute("PRAGMA user_version;").fetchone()[0]

    if current_version == 0:
        # 初始架構建立
        conn.execute(CREATE_WATCHLIST_TABLE_SQL)
        conn.execute(CREATE_WATCHLIST_CATEGORY_INDEX)
        conn.execute(CREATE_WATCHLIST_ENABLED_INDEX)
        conn.execute("PRAGMA user_version = 1;")
        conn.commit()

    # 未來的遷移寫在這裡
    # if current_version == 1:
    #     conn.execute("ALTER TABLE watchlist ADD COLUMN new_field TEXT;")
    #     conn.execute("PRAGMA user_version = 2;")
    #     conn.commit()
