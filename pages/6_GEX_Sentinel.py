"""
GEX Sentinel Watchlist Dashboard - Main Streamlit Page

Feature: 001-gex-sentinel-watchlist
User Stories: P1 (Watchlist Management), P2 (Scanner), P3 (Deep Dive), P4 (Categorization)
"""

import streamlit as st
from src.database.db import initialize_db
from src.ui.sidebar import render_watchlist_management
from src.services.watchlist_service import get_all_symbols

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

# Render sidebar watchlist management (User Story 1 - P1 MVP)
def on_symbol_removed(symbol: str):
    """Callback when symbol is removed - refresh main view"""
    # Clear any cached data for this symbol
    st.cache_data.clear()

render_watchlist_management(on_symbol_removed=on_symbol_removed)

# Main content area
st.divider()

# Get current watchlist
watchlist = get_all_symbols()

if not watchlist:
    # Empty state (onboarding message per edge case spec)
    st.info("""
    ### 👋 Welcome to GEX Sentinel!

    Your watchlist is empty. Add symbols in the sidebar to start monitoring market structure:

    - **GEX (Gamma Exposure)**: See dealer positioning and potential support/resistance
    - **Max Pain**: Identify where options expire worthless
    - **Volatility Metrics**: Track IV percentile and Put/Call ratios
    - **AI Analysis**: Get structure interpretation for key symbols

    **Getting Started**: Add a liquid stock with active options (e.g., NVDA, AAPL, SPY) using the sidebar input above.
    """)

else:
    # Display watchlist summary
    st.subheader(f"Monitoring {len(watchlist)} Symbol(s)")

    # Display symbols in columns
    cols = st.columns(min(len(watchlist), 5))
    for idx, entry in enumerate(watchlist[:5]):  # Show first 5 in pills
        with cols[idx]:
            if entry.category:
                st.metric(label=entry.symbol, value=entry.category)
            else:
                st.metric(label=entry.symbol, value="—")

    if len(watchlist) > 5:
        st.caption(f"...and {len(watchlist) - 5} more symbols")

    st.divider()

    # Placeholder for Scanner Table (User Story 2 - P2)
    st.info("""
    ### 🚧 Scanner Table View (Coming Next)

    Phase 2 will display:
    - Current Price & Change %
    - GEX State (Bullish/Bearish)
    - Max Pain Distance
    - Call Wall / Put Wall

    **Status**: User Story 2 (P2) - Implementation in progress
    """)

    # Placeholder for Deep Dive (User Story 3 - P3)
    with st.expander("🔍 Deep Dive Analysis (Coming Soon)"):
        st.info("""
        Select a symbol from the scanner table to view:
        - **Structure Card**: Net GEX, Trending/Ranging status
        - **Walls Visualization**: Call Wall, Max Pain, Put Wall
        - **Sentiment Indicators**: RSI gauge, Put/Call Ratio
        - **AI Analysis**: Structure interpretation with specific GEX levels

        **Status**: User Story 3 (P3) - Not yet implemented
        """)

# Footer
st.divider()
st.caption("Built with ❤️ | Constitution Principles: Privacy-First | Performance Through Caching | Structure Over Price")
