"""
GEX (Gamma Exposure) calculator service.

Implements GEX proxy algorithm per research.md Section 1.
Calculates Net GEX, GEX State, Call/Put Walls, and Max Pain.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm
from typing import Optional

from src.models.gex_profile import GEXProfile
from src.services.market_data_service import fetch_options_chain, fetch_price_snapshot


@st.cache_data(ttl=300)
def calculate_gex_profile(symbol: str) -> GEXProfile:
    """
    Calculate GEX metrics from options chain (cached 5 min).

    Args:
        symbol: Ticker symbol

    Returns:
        GEXProfile: Net GEX, GEX state, Call/Put walls, Max Pain

    Raises:
        ValueError: No options chain available (illiquid stock)
        RuntimeError: GEX calculation timeout (>2s)

    Algorithm (from research.md):
        gex_per_strike = OI × gamma × 100 × spot_price² × 0.01
        net_gex = sum(call_gex) - sum(put_gex)
        gex_state = "Bullish" if net_gex > 0 else ("Neutral" if net_gex == 0 else "Bearish")

    Performance Requirement: Must complete in <2s (PERF-002)
    Caching: @st.cache_data(ttl=300) on (symbol,)
    """
    # Fetch options chain and current price
    options_chain = fetch_options_chain(symbol)
    price_snapshot = fetch_price_snapshot(symbol)

    spot_price = price_snapshot.current_price
    calls_df = options_chain.calls
    puts_df = options_chain.puts

    # Calculate time to expiry (simplified: assume 30 days)
    # TODO: Parse expiry_date properly for exact TTE
    tte_years = 30 / 365.0

    # Calculate gamma for each strike and compute GEX
    call_gex_total = 0.0
    for _, row in calls_df.iterrows():
        strike = row['strike']
        oi = row['openInterest']
        iv = row.get('impliedVolatility', 0.25)  # Default IV if missing

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

    # Net GEX
    net_gex = call_gex_total - put_gex_total

    # GEX State
    if net_gex > 0:
        gex_state = "Bullish"
    elif net_gex < 0:
        gex_state = "Bearish"
    else:
        gex_state = "Neutral"

    # Calculate walls (highest OI strikes)
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

    # Calculate Max Pain
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
    Calculate Black-Scholes gamma for a strike (internal helper).

    Args:
        strike: Strike price
        spot: Current stock price
        iv: Implied volatility (annualized, 0.0-1.0)
        tte: Time to expiry (years)

    Returns:
        float: Gamma value

    Formula (from service_contracts.md):
        d1 = (log(spot/strike) + (0.025 + 0.5*iv²)*tte) / (iv*sqrt(tte))
        gamma = norm.pdf(d1) / (spot * iv * sqrt(tte))

    Library: scipy.stats.norm for norm.pdf
    """
    if iv <= 0 or tte <= 0 or spot <= 0 or strike <= 0:
        return 0.0

    try:
        # Risk-free rate assumed at 2.5% (0.025)
        d1 = (np.log(spot / strike) + (0.025 + 0.5 * iv ** 2) * tte) / (iv * np.sqrt(tte))
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(tte))
        return gamma
    except:
        return 0.0


def _calculate_max_pain(options_chain, spot_price: float) -> Optional[float]:
    """
    Find strike with minimum total intrinsic value loss (internal helper).

    Args:
        options_chain: OptionsChain with calls + puts DataFrames
        spot_price: Current stock price (for proximity check)

    Returns:
        float: Max Pain strike price

    Algorithm (from service_contracts.md):
        for strike in all_strikes:
            call_loss = sum(max(0, spot - s) * oi for s in calls if s > strike)
            put_loss = sum(max(0, s - spot) * oi for s in puts if s < strike)
            total_loss[strike] = call_loss + put_loss

        max_pain = min(total_loss, key=total_loss.get)
    """
    calls_df = options_chain.calls
    puts_df = options_chain.puts

    # Get all unique strikes
    all_strikes = sorted(set(calls_df['strike'].tolist() + puts_df['strike'].tolist()))

    if not all_strikes:
        return None

    # Calculate total intrinsic value loss for each potential Max Pain strike
    total_losses = {}

    for pain_strike in all_strikes:
        # Call losses: For strikes above pain_strike, calculate ITM value
        call_loss = 0.0
        for _, row in calls_df.iterrows():
            strike = row['strike']
            oi = row['openInterest']
            if strike < pain_strike:
                # Calls ITM at expiry
                call_loss += max(0, pain_strike - strike) * oi * 100  # Contract multiplier

        # Put losses: For strikes below pain_strike, calculate ITM value
        put_loss = 0.0
        for _, row in puts_df.iterrows():
            strike = row['strike']
            oi = row['openInterest']
            if strike > pain_strike:
                # Puts ITM at expiry
                put_loss += max(0, strike - pain_strike) * oi * 100

        total_losses[pain_strike] = call_loss + put_loss

    # Max Pain is the strike with minimum total loss
    max_pain_strike = min(total_losses, key=total_losses.get)

    return float(max_pain_strike)
