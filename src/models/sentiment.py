"""
情緒指標資料模型。

根據 data-model.md 第 4 節的動能和選擇權部位技術指標。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SentimentIndicators:
    """
    動能和選擇權部位的技術指標 (衍生，不持久化)。

    Attributes:
        symbol: 股票代碼
        rsi: 相對強弱指數 (14 週期)，範圍 [0, 100]
        pcr: Put/Call 比率 (總 Put OI / 總 Call OI)
        iv_percentile: 隱含波動率相對於 52 週歷史的排名，範圍 [0, 100]
        timestamp: 指標計算的時間

    Validation Rules:
    - rsi 限制在 [0, 100] 範圍內
    - pcr 不能為負數 (若無 calls 則為 0，若無限大則上限為 10.0)
    - iv_percentile = percentile_rank(current_iv, 52_week_iv_history)

    Calculation Notes:
    - RSI: 基於每日收盤價的標準 14 週期 Wilder's RSI
    - PCR: 所有履約價的 sum(put_OI) / sum(call_OI)
    - IV Percentile: 獲取 52 週的歷史 IV → 計算當前 IV 的百分位數
    """

    symbol: str
    rsi: float  # Range: [0, 100]
    pcr: float  # Put/Call Ratio (capped at 10.0)
    iv_percentile: float  # Range: [0, 100]
    timestamp: datetime
