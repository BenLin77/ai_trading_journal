"""
GEX Sentinel Watchlist Dashboard - Main Streamlit Page

Feature: 001-gex-sentinel-watchlist
User Stories: P1 (Watchlist Management), P2 (Scanner), P3 (Deep Dive), P4 (Categorization)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

from src.database.db import initialize_db
from src.ui.sidebar import render_watchlist_management
from src.services.watchlist_service import get_all_symbols, WatchlistEntry
from src.services.market_data_service import fetch_price_snapshot
from src.services.gex_calculator import calculate_gex_profile
from src.services.sentiment_service import calculate_sentiment_indicators
from src.services.ai_service import generate_structure_analysis
from src.models.gex_profile import GEXProfile, MarketSnapshot
from src.models.sentiment import SentimentIndicators

# Page configuration
st.set_page_config(
    page_title="GEX Sentinel | AI Trading Coach",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on first run
initialize_db()

# Title
st.title("📊 GEX Sentinel Watchlist Dashboard")
st.caption("User-managed watchlist with batch GEX/Max Pain calculations and deep-dive structure analysis")

# --- Sidebar Watchlist Management (User Story 1 - P1 MVP) ---
def on_symbol_removed(symbol: str):
    """Callback when symbol is removed - refresh main view"""
    st.cache_data.clear()
    st.rerun()

render_watchlist_management(on_symbol_removed=on_symbol_removed)

# --- Data Fetching & Processing ---

@st.cache_data(ttl=300)
def fetch_symbol_data(symbol: str):
    """Fetch all data for a single symbol with error handling."""
    try:
        price_snap = fetch_price_snapshot(symbol)
        gex_prof = calculate_gex_profile(symbol)
        sentiment = calculate_sentiment_indicators(symbol)
        return {
            "status": "success",
            "price": price_snap,
            "gex": gex_prof,
            "sentiment": sentiment
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def fetch_batch_data(watchlist):
    """Fetch data for all symbols in watchlist with progress bar."""
    results = {}
    if not watchlist:
        return results
        
    progress_bar = st.progress(0, text="Initializing batch fetch...")
    
    for i, entry in enumerate(watchlist):
        progress_bar.progress((i + 1) / len(watchlist), text=f"Analyzing {entry.symbol}...")
        results[entry.symbol] = fetch_symbol_data(entry.symbol)
    
    progress_bar.empty()
    return results

# --- UI Components ---

def render_scanner_table(watchlist, data_map):
    """Render User Story 2: Scanner Table View."""
    st.subheader("📡 Market Scanner")
    
    table_data = []
    for entry in watchlist:
        symbol = entry.symbol
        data = data_map.get(symbol)
        
        if not data or data["status"] == "error":
            table_data.append({
                "Symbol": symbol,
                "Price": "Error",
                "Change": "---",
                "GEX State": "⚠️ Data Unavailable",
                "Max Pain": "---",
                "Walls (Call/Put)": "---",
                "Category": entry.category or "—"
            })
            continue
            
        price: MarketSnapshot = data["price"]
        gex: GEXProfile = data["gex"]
        
        # Format Price Change
        change_str = f"{price.change_pct:+.2f}%"
        
        # Format Max Pain Distance
        if gex.max_pain:
            dist_pct = ((gex.max_pain - price.current_price) / price.current_price) * 100
            mp_str = f"${gex.max_pain:.2f} ({dist_pct:+.1f}%)"
        else:
            mp_str = "N/A"
            
        # Format Walls
        walls_str = f"C: ${gex.call_wall} / P: ${gex.put_wall}" if (gex.call_wall and gex.put_wall) else "N/A"
        
        # GEX State Badge
        state_icon = "🐂" if gex.gex_state == "Bullish" else "🐻" if gex.gex_state == "Bearish" else "⚖️"
        state_display = f"{state_icon} {gex.gex_state}"

        table_data.append({
            "Symbol": symbol,
            "Price": price.current_price,
            "Change %": price.change_pct,
            "GEX State": state_display,
            "Max Pain": mp_str,
            "Walls (Call/Put)": walls_str,
            "Category": entry.category or "—",
            "_raw_change": price.change_pct  # Hidden for styling if needed
        })
        
    if not table_data:
        return

    df = pd.DataFrame(table_data)
    
    # Style the dataframe
    st.dataframe(
        df,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "Change %": st.column_config.NumberColumn(format="%.2f%%"),
        },
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="scanner_selection"
    )
    
    return df

def render_deep_dive(symbol: str, data: dict):
    """Render User Story 3: Deep Dive Analysis."""
    st.divider()
    st.header(f"🔍 Deep Dive: {symbol}")
    
    if data["status"] == "error":
        st.error(f"Unable to load analysis for {symbol}: {data['error']}")
        return

    price: MarketSnapshot = data["price"]
    gex: GEXProfile = data["gex"]
    sent: SentimentIndicators = data["sentiment"]
    
    # --- Top Level Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${price.current_price:.2f}", f"{price.change_pct:+.2f}%")
    col2.metric("Net GEX", f"${gex.net_gex / 1_000_000_000:.2f}B", delta_color="off")
    col3.metric("RSI (14)", f"{sent.rsi:.1f}")
    col4.metric("IV Percentile", f"{sent.iv_percentile:.0f}%")
    
    # --- Structure Cards ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("🏰 GEX Walls & Levels")
        st.info(f"""
        **Call Wall (Resistance):** ${gex.call_wall}
        
        **Max Pain (Magnet):** ${gex.max_pain}
        
        **Put Wall (Support):** ${gex.put_wall}
        """)
    
    with c2:
        st.subheader("🌡️ Sentiment & Positioning")
        pcr_delta = "Neutral"
        if sent.pcr > 1.0: pcr_delta = "Bearish (High Puts)"
        elif sent.pcr < 0.7: pcr_delta = "Bullish (High Calls)"
        
        st.success(f"""
        **Put/Call Ratio:** {sent.pcr:.2f} ({pcr_delta})
        
        **GEX State:** {gex.gex_state}
        
        **Volatility:** IV Rank is {sent.iv_percentile:.0f}% of 52-week range
        """)

    # --- AI Analysis ---
    st.subheader("🤖 AI Structure Analyst")
    
    if "ai_analysis_cache" not in st.session_state:
        st.session_state.ai_analysis_cache = {}
        
    cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H')}"
    
    if st.button(f"Generate Analysis for {symbol}", type="primary"):
        with st.spinner("Consulting AI Analyst..."):
            try:
                if cache_key in st.session_state.ai_analysis_cache:
                    analysis = st.session_state.ai_analysis_cache[cache_key]
                else:
                    analysis = generate_structure_analysis(symbol, gex, sent)
                    st.session_state.ai_analysis_cache[cache_key] = analysis
                
                st.markdown(analysis)
            except Exception as e:
                st.error(f"Analysis generation failed: {e}")

# --- Main Execution Flow ---

st.divider()

# Get current watchlist
watchlist = get_all_symbols()

if not watchlist:
    # Empty state
    st.info("""
    ### 👋 Welcome to GEX Sentinel!
    Your watchlist is empty. Add symbols in the sidebar to start monitoring market structure.
    """)
else:
    # 1. Batch Fetch Data
    data_map = fetch_batch_data(watchlist)
    
    # 2. Render Scanner Table
    render_scanner_table(watchlist, data_map)
    
    # 3. Check for Selection
    selection = st.session_state.get("scanner_selection")
    if selection and selection["selection"]["rows"]:
        selected_idx = selection["selection"]["rows"][0]
        if selected_idx < len(watchlist):
            selected_symbol = watchlist[selected_idx].symbol
            
            # 4. Render Render Deep Dive
            if selected_symbol in data_map:
                render_deep_dive(selected_symbol, data_map[selected_symbol])

# Footer
st.divider()
st.caption("Built with ❤️ | Constitution Principles: Privacy-First | Performance Through Caching | Structure Over Price")
