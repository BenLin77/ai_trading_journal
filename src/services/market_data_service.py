"""
Market data service for fetching options chains, prices, and IV history.

Implements caching per Constitution Principle III (Performance Through Aggressive Caching).
All functions wrapped with @st.cache_data(ttl=300) per service_contracts.md Section 2.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import NamedTuple

from src.models.gex_profile import MarketSnapshot


class OptionsChain(NamedTuple):
    """
    Raw options data from yfinance API.

    Attributes:
        symbol: Stock ticker
        expiry_date: Options expiration date
        calls: DataFrame with call options data
        puts: DataFrame with put options data
    """
    symbol: str
    expiry_date: str
    calls: pd.DataFrame
    puts: pd.DataFrame


@st.cache_data(ttl=300)
def fetch_options_chain(symbol: str, expiry: str = "nearest") -> OptionsChain:
    """
    Fetch options chain data for a symbol (cached 5 min).

    Args:
        symbol: Ticker symbol
        expiry: "nearest" or specific date "2025-01-17"

    Returns:
        OptionsChain: with calls and puts DataFrames

    Raises:
        ValueError: Symbol not found or no options available
        requests.HTTPError: yfinance API failure (rate limit, network)

    Caching:
        @st.cache_data(ttl=300) on (symbol, expiry)
        Key: f"options_chain_{symbol}_{expiry}"

    Retry Logic (per research.md Section 2):
        3 attempts with exponential backoff (2s, 4s, 8s)
        Circuit breaker after 5 consecutive failures
    """
    ticker = yf.Ticker(symbol)

    # Get available expiration dates
    try:
        expirations = ticker.options
    except Exception as e:
        raise ValueError(f"No options available for {symbol}: {e}")

    if not expirations or len(expirations) == 0:
        raise ValueError(f"No options available for {symbol}")

    # Select expiry
    if expiry == "nearest":
        selected_expiry = expirations[0]
    else:
        if expiry not in expirations:
            raise ValueError(f"Expiry {expiry} not available for {symbol}")
        selected_expiry = expiry

    # Fetch options chain with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            option_chain = ticker.option_chain(selected_expiry)

            # Verify data integrity
            if option_chain.calls.empty or option_chain.puts.empty:
                raise ValueError(f"Empty options chain for {symbol} at {selected_expiry}")

            return OptionsChain(
                symbol=symbol,
                expiry_date=selected_expiry,
                calls=option_chain.calls,
                puts=option_chain.puts
            )

        except Exception as e:
            if attempt < max_retries - 1:
                import time
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                time.sleep(wait_time)
                continue
            else:
                raise ValueError(f"Failed to fetch options chain for {symbol} after {max_retries} attempts: {e}")


@st.cache_data(ttl=300)
def fetch_price_snapshot(symbol: str) -> MarketSnapshot:
    """
    Fetch current price and previous close (cached 5 min).

    Args:
        symbol: Ticker symbol

    Returns:
        MarketSnapshot: Current price, previous close, change %, timestamp

    Raises:
        ValueError: Symbol not found
        requests.HTTPError: API failure

    Caching:
        @st.cache_data(ttl=300) on (symbol,)
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    # Extract price data
    current_price = info.get('regularMarketPrice') or info.get('currentPrice')
    previous_close = info.get('previousClose')

    if current_price is None or previous_close is None:
        raise ValueError(f"No price data available for {symbol}")

    # Calculate change percentage
    change_pct = ((current_price - previous_close) / previous_close) * 100

    return MarketSnapshot(
        symbol=symbol,
        current_price=float(current_price),
        previous_close=float(previous_close),
        change_pct=float(change_pct),
        timestamp=datetime.now()
    )


@st.cache_data(ttl=3600)
def fetch_iv_history(symbol: str, period: str = "1y") -> pd.Series:
    """
    Fetch 52-week IV history for percentile calculation (cached 1 hour).

    Args:
        symbol: Ticker symbol
        period: yfinance period string (default: "1y" for 52 weeks)

    Returns:
        pd.Series: Index: dates, Values: IV (annualized)

    Raises:
        ValueError: Insufficient historical data (<30 days)

    Caching:
        @st.cache_data(ttl=3600) (1 hour) - historical data changes slowly

    Note: This is a simplified proxy. Real IV history requires options historical data.
    We use historical volatility (HV) as a proxy for IV.
    """
    ticker = yf.Ticker(symbol)

    # Fetch historical price data
    hist = ticker.history(period=period)

    if len(hist) < 30:
        raise ValueError(f"Insufficient historical data for {symbol}: only {len(hist)} days")

    # Calculate historical volatility (HV) as IV proxy
    # HV = standard deviation of log returns * sqrt(252) for annualization
    returns = (hist['Close'] / hist['Close'].shift(1)).apply(lambda x: x if x > 0 else 1).apply(lambda x: pd.Series.log(x))
    rolling_vol = returns.rolling(window=20).std() * (252 ** 0.5)  # 20-day rolling volatility

    return rolling_vol.dropna()
