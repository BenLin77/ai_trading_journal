"""
觀察清單資料模型。

根據 data-model.md 第 1 節代表使用者追蹤的股票代碼。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WatchlistEntry:
    """
    代表監控清單中使用者追蹤的股票代碼。

    Attributes:
        id: 資料庫資料列的唯一識別碼
        symbol: 股票代碼 (例如 "NVDA", "AMD")
        added_at: 新增股票的時間戳記
        category: 可選分組 (例如 "Tech", "Core")
        notes: 使用者註釋 (未來增強功能)
        enabled: 啟用/停用旗標 (未來: 停用而不刪除)

    Validation Rules (enforced in service layer):
    - symbol 必須為大寫
    - symbol 必須是有效的股票代碼 (插入前透過 yfinance 驗證)
    - 若實作 P4，category 限制在預定義清單中
    """

    id: int
    symbol: str
    added_at: datetime
    category: Optional[str] = None
    notes: Optional[str] = None
    enabled: bool = True
