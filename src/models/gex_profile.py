"""
GEX Profile and Market Snapshot data models.

Calculated market structure metrics per data-model.md Sections 2-3.
These are ephemeral (derived, not persisted).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GEXProfile:
    """
    Calculated market structure snapshot for a single symbol (derived, not persisted).

    Attributes:
        symbol: Stock ticker
        net_gex: Net gamma exposure in dollars (calls - puts)
        gex_state: "Bullish" (net_gex > 0), "Bearish" (net_gex < 0), or "Neutral" (net_gex == 0)
        call_wall: Strike with highest call open interest
        put_wall: Strike with highest put open interest
        max_pain: Strike with minimum total intrinsic value
        timestamp: When calculation was performed

    Validation Rules:
    - gex_state derived from sign of net_gex
    - call_wall and put_wall must be valid strikes from options chain
    - max_pain must be within active strike range

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
    Current price and change data for a symbol (derived, not persisted).

    Attributes:
        symbol: Stock ticker
        current_price: Latest trade price
        previous_close: Prior session close
        change_pct: Percentage change (current - prev) / prev
        timestamp: When data was fetched

    Validation Rules:
    - change_pct = (current_price - previous_close) / previous_close * 100
    - current_price and previous_close must be positive
    """

    symbol: str
    current_price: float
    previous_close: float
    change_pct: float
    timestamp: datetime
