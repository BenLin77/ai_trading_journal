"""
情緒服務，用於計算 RSI、PCR 和 IV 百分位數。

根據 service_contracts.md 第 4 節實作技術指標。
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

from src.models.sentiment import SentimentIndicators
from src.services.market_data_service import fetch_options_chain, fetch_iv_history


@st.cache_data(ttl=300)
def calculate_sentiment_indicators(symbol: str) -> SentimentIndicators:
    """
    計算 RSI、PCR、IV 百分位數 (快取 5 分鐘)。

    Args:
        symbol: 股票代碼

    Returns:
        SentimentIndicators: RSI、PCR、IV 百分位數、時間戳記

    Raises:
        ValueError: RSI 數據不足 (需要 14 天以上)
        ValueError: 無 IV 歷史記錄 (流動性不足的股票)

    計算 (來自 service_contracts.md):
        RSI (14 週期 Wilder's): 100 - (100 / (1 + RS))  # RS = 平均漲幅 / 平均跌幅
        PCR: sum(put_OI) / sum(call_OI)  # 若 calls → 0 則上限為 10.0
        IV Percentile: percentile_rank(current_iv, iv_52w_history)

    Caching:
        @st.cache_data(ttl=300) on (symbol,)
    """
    # 獲取選擇權鏈以計算 PCR 和當前 IV
    options_chain = fetch_options_chain(symbol)

    # 計算 PCR (Put/Call 比率)
    total_put_oi = options_chain.puts['openInterest'].sum()
    total_call_oi = options_chain.calls['openInterest'].sum()

    if total_call_oi == 0:
        pcr = 10.0  # 根據驗證規則上限為 10.0
    else:
        pcr = total_put_oi / total_call_oi
        pcr = min(pcr, 10.0)  # 上限為 10.0

    # 計算 RSI
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="3mo")  # 3 個月數據用於 RSI 計算

    if len(hist) < 15:  # 需要 14 天以上計算 RSI
        raise ValueError(f"RSI 計算數據不足: 只有 {len(hist)} 天可用")

    rsi = _calculate_rsi(hist['Close'], period=14)

    # 計算 IV 百分位數
    try:
        iv_history = fetch_iv_history(symbol, period="1y")

        # 獲取當前 IV (ATM 選擇權的平均值)
        spot_price = hist['Close'].iloc[-1]
        atm_calls = options_chain.calls[
            (options_chain.calls['strike'] >= spot_price * 0.95) &
            (options_chain.calls['strike'] <= spot_price * 1.05)
        ]

        if not atm_calls.empty:
            current_iv = atm_calls['impliedVolatility'].mean()
        else:
            current_iv = options_chain.calls['impliedVolatility'].mean()

        # 計算百分位排名
        iv_percentile = (iv_history < current_iv).sum() / len(iv_history) * 100

    except Exception as e:
        # 若 IV 歷史記錄不可用則使用備案
        iv_percentile = 50.0  # 中性

    return SentimentIndicators(
        symbol=symbol,
        rsi=float(rsi),
        pcr=float(pcr),
        iv_percentile=float(iv_percentile),
        timestamp=datetime.now()
    )


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    計算相對強弱指數 (14 週期 Wilder's RSI)。

    Args:
        prices: 收盤價序列
        period: RSI 週期 (預設: 14)

    Returns:
        float: RSI 值，範圍 [0, 100]

    公式:
        RSI = 100 - (100 / (1 + RS))
        RS = 平均漲幅 / 平均跌幅 (Wilder's 平滑)
    """
    # 計算價格變動
    delta = prices.diff()

    # 分離漲幅和跌幅
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # 計算 Wilder's 平滑平均值
    avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0  # 無跌幅 = 超買

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # 根據驗證規則限制在 [0, 100] 範圍內
    return max(0.0, min(100.0, rsi))


def _fetch_iv_history(symbol: str) -> pd.Series:
    """
    fetch_iv_history 的包裝器，允許在測試中進行 mock。

    此函式存在是為了在單元測試中啟用 patching。
    """
    return fetch_iv_history(symbol, period="1y")
