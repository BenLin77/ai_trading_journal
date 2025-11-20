"""
Sentiment Indicators data model.

Technical indicators for momentum and options positioning per data-model.md Section 4.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SentimentIndicators:
    """
    Technical indicators for momentum and options positioning (derived, not persisted).

    Attributes:
        symbol: Stock ticker
        rsi: Relative Strength Index (14-period), range [0, 100]
        pcr: Put/Call Ratio (total put OI / total call OI)
        iv_percentile: Implied Volatility rank vs 52-week history, range [0, 100]
        timestamp: When indicators were calculated

    Validation Rules:
    - rsi clamped to [0, 100] range
    - pcr cannot be negative (0 if no calls, cap at 10.0 if infinity)
    - iv_percentile = percentile_rank(current_iv, 52_week_iv_history)

    Calculation Notes:
    - RSI: Standard 14-period Wilder's RSI on daily close prices
    - PCR: sum(put_OI) / sum(call_OI) across all strikes
    - IV Percentile: Fetch 52 weeks of historical IV → calculate percentile of current IV
    """

    symbol: str
    rsi: float  # Range: [0, 100]
    pcr: float  # Put/Call Ratio (capped at 10.0)
    iv_percentile: float  # Range: [0, 100]
    timestamp: datetime
