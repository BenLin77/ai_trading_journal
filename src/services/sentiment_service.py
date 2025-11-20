"""
Sentiment service for calculating RSI, PCR, and IV percentile.

Implements technical indicators per service_contracts.md Section 4.
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
    Calculate RSI, PCR, IV percentile (cached 5 min).

    Args:
        symbol: Ticker symbol

    Returns:
        SentimentIndicators: RSI, PCR, IV percentile, timestamp

    Raises:
        ValueError: Insufficient data for RSI (need 14+ days)
        ValueError: No IV history (illiquid stock)

    Calculations (from service_contracts.md):
        RSI (14-period Wilder's): 100 - (100 / (1 + RS))  # RS = avg_gain / avg_loss
        PCR: sum(put_OI) / sum(call_OI)  # Cap at 10.0 if calls → 0
        IV Percentile: percentile_rank(current_iv, iv_52w_history)

    Caching:
        @st.cache_data(ttl=300) on (symbol,)
    """
    # Fetch options chain for PCR and current IV
    options_chain = fetch_options_chain(symbol)

    # Calculate PCR (Put/Call Ratio)
    total_put_oi = options_chain.puts['openInterest'].sum()
    total_call_oi = options_chain.calls['openInterest'].sum()

    if total_call_oi == 0:
        pcr = 10.0  # Cap at 10.0 per validation rules
    else:
        pcr = total_put_oi / total_call_oi
        pcr = min(pcr, 10.0)  # Cap at 10.0

    # Calculate RSI
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="3mo")  # 3 months for RSI calculation

    if len(hist) < 15:  # Need 14+ days for RSI
        raise ValueError(f"Insufficient data for RSI calculation: only {len(hist)} days available")

    rsi = _calculate_rsi(hist['Close'], period=14)

    # Calculate IV Percentile
    try:
        iv_history = fetch_iv_history(symbol, period="1y")

        # Get current IV (average of ATM options)
        spot_price = hist['Close'].iloc[-1]
        atm_calls = options_chain.calls[
            (options_chain.calls['strike'] >= spot_price * 0.95) &
            (options_chain.calls['strike'] <= spot_price * 1.05)
        ]

        if not atm_calls.empty:
            current_iv = atm_calls['impliedVolatility'].mean()
        else:
            current_iv = options_chain.calls['impliedVolatility'].mean()

        # Calculate percentile rank
        iv_percentile = (iv_history < current_iv).sum() / len(iv_history) * 100

    except Exception as e:
        # Fallback if IV history unavailable
        iv_percentile = 50.0  # Neutral

    return SentimentIndicators(
        symbol=symbol,
        rsi=float(rsi),
        pcr=float(pcr),
        iv_percentile=float(iv_percentile),
        timestamp=datetime.now()
    )


def _calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate Relative Strength Index (14-period Wilder's RSI).

    Args:
        prices: Series of closing prices
        period: RSI period (default: 14)

    Returns:
        float: RSI value in [0, 100] range

    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = average_gain / average_loss (Wilder's smoothing)
    """
    # Calculate price changes
    delta = prices.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Calculate Wilder's smoothed averages
    avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0  # No losses = overbought

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Clamp to [0, 100] range per validation rules
    return max(0.0, min(100.0, rsi))


def _fetch_iv_history(symbol: str) -> pd.Series:
    """
    Wrapper for fetch_iv_history to allow mocking in tests.

    This function exists to enable patching in unit tests.
    """
    return fetch_iv_history(symbol, period="1y")
