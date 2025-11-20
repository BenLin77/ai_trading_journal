"""
GEX (Gamma Exposure) 計算服務。

根據 research.md 第 1 節實作 GEX 代理演算法。
計算淨 GEX、GEX 狀態、Call/Put 牆和最大痛點 (Max Pain)。
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import logging
from scipy.stats import norm
from typing import Optional

from src.models.gex_profile import GEXProfile
from src.services.market_data_service import fetch_options_chain, fetch_price_snapshot


@st.cache_data(ttl=300)
def calculate_gex_profile(symbol: str) -> GEXProfile:
    """
    從選擇權鏈計算 GEX 指標 (快取 5 分鐘)。

    Args:
        symbol: 股票代碼

    Returns:
        GEXProfile: 淨 GEX、GEX 狀態、Call/Put 牆、最大痛點

    Raises:
        ValueError: 無可用選擇權鏈 (流動性不足的股票)
        RuntimeError: GEX 計算超時 (>2s)

    演算法 (來自 research.md):
        gex_per_strike = OI × gamma × 100 × spot_price² × 0.01
        net_gex = sum(call_gex) - sum(put_gex)
        gex_state = "Bullish" if net_gex > 0 else ("Neutral" if net_gex == 0 else "Bearish")

    效能需求: 必須在 <2s 內完成 (PERF-002)
    快取: @st.cache_data(ttl=300) on (symbol,)
    """
    start_time = time.time()
    
    # 獲取選擇權鏈和當前價格
    options_chain = fetch_options_chain(symbol)
    price_snapshot = fetch_price_snapshot(symbol)

    spot_price = price_snapshot.current_price
    calls_df = options_chain.calls
    puts_df = options_chain.puts

    # 計算到期時間 (使用實際到期日)
    try:
        expiry_date = datetime.strptime(options_chain.expiry_date, "%Y-%m-%d")
        # 加上 16:00 作為收盤時間，讓計算更精確
        expiry_datetime = expiry_date.replace(hour=16, minute=0, second=0)
        
        time_diff = expiry_datetime - datetime.now()
        tte_days = time_diff.total_seconds() / (24 * 3600)
        
        # 確保至少有 1 天 (0.0027 年) 以避免除以零或極端 Gamma 值
        tte_years = max(tte_days, 1.0) / 365.0
    except Exception as e:
        logging.warning(f"無法解析到期日 {options_chain.expiry_date}: {e}，使用預設 30 天")
        tte_years = 30 / 365.0

    # 檢查超時 (PERF-002)
    # 在進入繁重計算迴圈前檢查
    if time.time() - start_time > 1.5: # 保守檢查
         logging.warning(f"{symbol} 的 GEX 計算在迴圈前接近超時")

    # 計算每個履約價的 Gamma 並計算 GEX
    call_gex_total = 0.0
    for _, row in calls_df.iterrows():
        strike = row['strike']
        oi = row['openInterest']
        iv = row.get('impliedVolatility', 0.25)  # 若缺失則使用預設 IV

        gamma = _calculate_gamma(strike, spot_price, iv, tte_years)
        gex_per_strike = oi * gamma * 100 * (spot_price ** 2) * 0.01
        call_gex_total += gex_per_strike

    put_gex_total = 0.0
    for _, row in puts_df.iterrows():
        strike = row['strike']
        oi = row['openInterest']
        iv = row.get('impliedVolatility', 0.25)

        gamma = _calculate_gamma(strike, spot_price, iv, tte_years)
        gex_per_strike = oi * gamma * 100 * (spot_price ** 2) * 0.01
        put_gex_total += gex_per_strike

    # 淨 GEX
    net_gex = call_gex_total - put_gex_total

    # GEX 狀態
    if net_gex > 0:
        gex_state = "Bullish"
    elif net_gex < 0:
        gex_state = "Bearish"
    else:
        gex_state = "Neutral"

    # 計算牆 (最高 OI 履約價)
    if not calls_df.empty and 'openInterest' in calls_df.columns:
        max_call_oi_idx = calls_df['openInterest'].idxmax()
        call_wall = float(calls_df.loc[max_call_oi_idx, 'strike'])
    else:
        call_wall = None

    if not puts_df.empty and 'openInterest' in puts_df.columns:
        max_put_oi_idx = puts_df['openInterest'].idxmax()
        put_wall = float(puts_df.loc[max_put_oi_idx, 'strike'])
    else:
        put_wall = None

    # 計算最大痛點 (Max Pain)
    max_pain = _calculate_max_pain(options_chain, spot_price)

    return GEXProfile(
        symbol=symbol,
        net_gex=net_gex,
        gex_state=gex_state,
        call_wall=call_wall,
        put_wall=put_wall,
        max_pain=max_pain,
        timestamp=datetime.now()
    )


def _calculate_gamma(strike: float, spot: float, iv: float, tte: float) -> float:
    """
    計算履約價的 Black-Scholes Gamma (內部輔助函式)。

    Args:
        strike: 履約價
        spot: 當前股價
        iv: 隱含波動率 (年化, 0.0-1.0)
        tte: 到期時間 (年)

    Returns:
        float: Gamma 值

    公式 (來自 service_contracts.md):
        d1 = (log(spot/strike) + (0.025 + 0.5*iv²)*tte) / (iv*sqrt(tte))
        gamma = norm.pdf(d1) / (spot * iv * sqrt(tte))

    函式庫: scipy.stats.norm 用於 norm.pdf
    """
    if iv <= 0 or tte <= 0 or spot <= 0 or strike <= 0:
        return 0.0

    try:
        # 假設無風險利率為 2.5% (0.025)
        d1 = (np.log(spot / strike) + (0.025 + 0.5 * iv ** 2) * tte) / (iv * np.sqrt(tte))
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(tte))
        return gamma
    except:
        return 0.0


def _calculate_max_pain(options_chain, spot_price: float) -> Optional[float]:
    """
    尋找總內在價值損失最小的履約價 (內部輔助函式)。

    Args:
        options_chain: 包含 calls + puts DataFrames 的 OptionsChain
        spot_price: 當前股價 (用於接近度檢查)

    Returns:
        float: 最大痛點履約價

    演算法 (來自 service_contracts.md):
        for strike in all_strikes:
            call_loss = sum(max(0, spot - s) * oi for s in calls if s > strike)
            put_loss = sum(max(0, s - spot) * oi for s in puts if s < strike)
            total_loss[strike] = call_loss + put_loss

        max_pain = min(total_loss, key=total_loss.get)
    """
    calls_df = options_chain.calls
    puts_df = options_chain.puts

    # 獲取所有唯一履約價
    all_strikes = sorted(set(calls_df['strike'].tolist() + puts_df['strike'].tolist()))

    if not all_strikes:
        return None

    # 計算每個潛在最大痛點履約價的總內在價值損失
    total_losses = {}

    for pain_strike in all_strikes:
        # Call 損失: 對於高於 pain_strike 的履約價，計算 ITM 價值
        call_loss = 0.0
        for _, row in calls_df.iterrows():
            strike = row['strike']
            oi = row['openInterest']
            if strike < pain_strike:
                # 到期時 Call 為 ITM
                call_loss += max(0, pain_strike - strike) * oi * 100  # 合約乘數

        # Put 損失: 對於低於 pain_strike 的履約價，計算 ITM 價值
        put_loss = 0.0
        for _, row in puts_df.iterrows():
            strike = row['strike']
            oi = row['openInterest']
            if strike > pain_strike:
                # 到期時 Put 為 ITM
                put_loss += max(0, strike - pain_strike) * oi * 100

        total_losses[pain_strike] = call_loss + put_loss

    # 最大痛點是總損失最小的履約價
    max_pain_strike = min(total_losses, key=total_losses.get)

    return float(max_pain_strike)
