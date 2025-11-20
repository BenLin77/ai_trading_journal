"""
GEX Profile 和 Market Snapshot 資料模型。

根據 data-model.md 第 2-3 節計算的市場結構指標。
這些是暫時性的 (衍生，不持久化)。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GEXProfile:
    """
    單一股票的市場結構快照 (衍生，不持久化)。

    Attributes:
        symbol: 股票代碼
        net_gex: 淨 Gamma 曝險金額 (calls - puts)
        gex_state: "Bullish" (net_gex > 0), "Bearish" (net_gex < 0), 或 "Neutral" (net_gex == 0)
        call_wall: 具有最高 Call 未平倉合約的履約價
        put_wall: 具有最高 Put 未平倉合約的履約價
        max_pain: 具有最小總內在價值的履約價
        timestamp: 執行計算的時間

    Validation Rules:
    - gex_state 衍生自 net_gex 的符號
    - call_wall 和 put_wall 必須是選擇權鏈中的有效履約價
    - max_pain 必須在活躍履約價範圍內

    Derivation Logic (from research.md):
        net_gex = sum(call_gex_per_strike) - sum(put_gex_per_strike)
        gex_state = "Bullish" if net_gex > 0 else ("Neutral" if net_gex == 0 else "Bearish")
        call_wall = max(call_strikes, key=lambda s: s.open_interest)
        put_wall = max(put_strikes, key=lambda s: s.open_interest)
        max_pain = min(all_strikes, key=lambda s: intrinsic_value_loss(s))
    """

    symbol: str
    net_gex: float
    gex_state: str  # "Bullish" | "Bearish" | "Neutral"
    call_wall: Optional[float]
    put_wall: Optional[float]
    max_pain: Optional[float]
    timestamp: datetime


@dataclass
class MarketSnapshot:
    """
    單一股票的當前價格和變動數據 (衍生，不持久化)。

    Attributes:
        symbol: 股票代碼
        current_price: 最新成交價
        previous_close: 前一交易日收盤價
        change_pct: 變動百分比 (current - prev) / prev
        timestamp: 獲取數據的時間

    Validation Rules:
    - change_pct = (current_price - previous_close) / previous_close * 100
    - current_price 和 previous_close 必須為正數
    """

    symbol: str
    current_price: float
    previous_close: float
    change_pct: float
    timestamp: datetime
