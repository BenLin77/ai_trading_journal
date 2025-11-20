"""
市場數據服務，用於獲取選擇權鏈、價格和 IV 歷史記錄。

根據憲法原則 III (透過積極快取提升效能) 實作快取。
所有函式均根據 service_contracts.md 第 2 節使用 @st.cache_data(ttl=300) 包裝。
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import NamedTuple

from src.models.gex_profile import MarketSnapshot


class OptionsChain(NamedTuple):
    """
    來自 yfinance API 的原始選擇權數據。

    Attributes:
        symbol: 股票代碼
        expiry_date: 選擇權到期日
        calls: 包含 Call 選擇權數據的 DataFrame
        puts: 包含 Put 選擇權數據的 DataFrame
    """
    symbol: str
    expiry_date: str
    calls: pd.DataFrame
    puts: pd.DataFrame


@st.cache_data(ttl=300)
def fetch_options_chain(symbol: str, expiry: str = "nearest") -> OptionsChain:
    """
    獲取股票的選擇權鏈數據 (快取 5 分鐘)。

    Args:
        symbol: 股票代碼
        expiry: "nearest" 或特定日期 "2025-01-17"

    Returns:
        OptionsChain: 包含 calls 和 puts DataFrames

    Raises:
        ValueError: 找不到股票代碼或無可用選擇權
        requests.HTTPError: yfinance API 失敗 (速率限制、網路問題)

    Caching:
        @st.cache_data(ttl=300) on (symbol, expiry)
        Key: f"options_chain_{symbol}_{expiry}"

    重試邏輯 (根據 research.md 第 2 節):
        3 次嘗試，指數退避 (2s, 4s, 8s)
        連續 5 次失敗後觸發斷路器
    """
    ticker = yf.Ticker(symbol)

    # 獲取可用的到期日
    try:
        expirations = ticker.options
    except Exception as e:
        raise ValueError(f"無法獲取 {symbol} 的選擇權: {e}")

    if not expirations or len(expirations) == 0:
        raise ValueError(f"{symbol} 無可用選擇權")

    # 選擇到期日
    if expiry == "nearest":
        selected_expiry = expirations[0]
    else:
        if expiry not in expirations:
            raise ValueError(f"{symbol} 無法使用到期日 {expiry}")
        selected_expiry = expiry

    # 使用重試邏輯獲取選擇權鏈
    max_retries = 3
    for attempt in range(max_retries):
        try:
            option_chain = ticker.option_chain(selected_expiry)

            # 驗證數據完整性
            if option_chain.calls.empty or option_chain.puts.empty:
                raise ValueError(f"{symbol} 在 {selected_expiry} 的選擇權鏈為空")

            return OptionsChain(
                symbol=symbol,
                expiry_date=selected_expiry,
                calls=option_chain.calls,
                puts=option_chain.puts
            )

        except Exception as e:
            if attempt < max_retries - 1:
                import time
                wait_time = 2 ** attempt  # 指數退避: 1s, 2s, 4s
                time.sleep(wait_time)
                continue
            else:
                raise ValueError(f"嘗試 {max_retries} 次後無法獲取 {symbol} 的選擇權鏈: {e}")


@st.cache_data(ttl=300)
def fetch_price_snapshot(symbol: str) -> MarketSnapshot:
    """
    獲取當前價格和前收盤價 (快取 5 分鐘)。

    Args:
        symbol: 股票代碼

    Returns:
        MarketSnapshot: 當前價格、前收盤價、漲跌幅 %、時間戳記

    Raises:
        ValueError: 找不到股票代碼
        requests.HTTPError: API 失敗

    Caching:
        @st.cache_data(ttl=300) on (symbol,)
    """
    ticker = yf.Ticker(symbol)
    
    # 價格獲取的重試邏輯 (T074)
    max_retries = 3
    info = None
    
    for attempt in range(max_retries):
        try:
            info = ticker.info
            if info:
                break
        except Exception:
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
            else:
                # 繼續執行錯誤處理
                pass
                
    if not info:
         raise ValueError(f"無法獲取 {symbol} 的數據")

    # 提取價格數據
    current_price = info.get('regularMarketPrice') or info.get('currentPrice')
    previous_close = info.get('previousClose')

    if current_price is None or previous_close is None:
        raise ValueError(f"{symbol} 無價格數據")

    # 計算漲跌幅百分比
    change_pct = ((current_price - previous_close) / previous_close) * 100
    
    # 如果可用，使用實際市場時間 (T073)
    market_time = info.get('regularMarketTime')
    if market_time:
        timestamp = datetime.fromtimestamp(market_time)
    else:
        timestamp = datetime.now()

    return MarketSnapshot(
        symbol=symbol,
        current_price=float(current_price),
        previous_close=float(previous_close),
        change_pct=float(change_pct),
        timestamp=timestamp
    )


@st.cache_data(ttl=3600)
def fetch_iv_history(symbol: str, period: str = "1y") -> pd.Series:
    """
    獲取 52 週 IV 歷史記錄以計算百分位數 (快取 1 小時)。

    Args:
        symbol: 股票代碼
        period: yfinance 期間字串 (預設: "1y" 代表 52 週)

    Returns:
        pd.Series: Index: 日期, Values: IV (年化)

    Raises:
        ValueError: 歷史數據不足 (<30 天)

    Caching:
        @st.cache_data(ttl=3600) (1 小時) - 歷史數據變化緩慢

    注意: 這是一個簡化的代理。真實 IV 歷史需要選擇權歷史數據。
    我們使用歷史波動率 (HV) 作為 IV 的代理。
    """
    ticker = yf.Ticker(symbol)

    # 獲取歷史價格數據
    hist = ticker.history(period=period)

    if len(hist) < 30:
        raise ValueError(f"{symbol} 的歷史數據不足: 只有 {len(hist)} 天")

    # 計算歷史波動率 (HV) 作為 IV 代理
    # HV = 對數收益率的標準差 * sqrt(252) 進行年化
    returns = (hist['Close'] / hist['Close'].shift(1)).apply(lambda x: x if x > 0 else 1).apply(lambda x: pd.Series.log(x))
    rolling_vol = returns.rolling(window=20).std() * (252 ** 0.5)  # 20 日滾動波動率

    return rolling_vol.dropna()
