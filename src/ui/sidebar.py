"""
Sidebar watchlist management UI component.

Per Constitution Principle II (User-Controlled Monitoring):
- Users have complete control over watchlist
- Explicit add/remove actions only
"""

import streamlit as st
import sqlite3
from typing import Callable

from src.services.watchlist_service import add_symbol, remove_symbol, get_all_symbols


def render_watchlist_management(on_symbol_removed: Callable[[str], None] = None):
    """
    Render watchlist management UI in sidebar.

    Args:
        on_symbol_removed: Optional callback when symbol is removed (for UI refresh)

    UI Components per contract:
    - Text input for symbol entry
    - "Add to Watchlist" button
    - Display current symbols with X (remove) buttons
    - Error/success messages via st.error/st.success/st.warning
    """
    st.sidebar.header("📊 Watchlist Management")

    # Input section
    with st.sidebar.form(key="add_symbol_form", clear_on_submit=True):
        symbol_input = st.text_input(
            "Symbol",
            placeholder="e.g., NVDA, AMD, TSLA",
            help="Enter a stock ticker symbol to add to your watchlist"
        )

        category_input = st.selectbox(
            "Category (Optional)",
            options=["", "Tech", "Core", "Speculative"],
            help="Organize symbols by category (optional)"
        )

        submit_button = st.form_submit_button("Add to Watchlist")

        if submit_button and symbol_input:
            try:
                # Add symbol with optional category
                cat = category_input if category_input else None
                entry = add_symbol(symbol_input, category=cat)

                st.success(f"✅ Added {entry.symbol} to watchlist")

            except sqlite3.IntegrityError:
                st.warning(f"⚠️ {symbol_input.upper()} is already in watchlist")

            except ValueError as e:
                st.error(f"❌ {str(e)}")

            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")

    # Display current watchlist
    st.sidebar.divider()
    st.sidebar.subheader("Current Watchlist")

    watchlist = get_all_symbols()

    if not watchlist:
        st.sidebar.info("Your watchlist is empty. Add symbols above to start monitoring market structure.")
    else:
        st.sidebar.caption(f"{len(watchlist)} symbol(s) tracked")

        for entry in watchlist:
            col1, col2 = st.sidebar.columns([4, 1])

            with col1:
                # Display symbol with category badge if present
                if entry.category:
                    st.write(f"**{entry.symbol}** `{entry.category}`")
                else:
                    st.write(f"**{entry.symbol}**")

            with col2:
                # Remove button
                if st.button("✖", key=f"remove_{entry.symbol}", help=f"Remove {entry.symbol}"):
                    if remove_symbol(entry.symbol):
                        st.success(f"Removed {entry.symbol}")

                        # Trigger callback if provided
                        if on_symbol_removed:
                            on_symbol_removed(entry.symbol)

                        # Force rerun to refresh UI
                        st.rerun()
                    else:
                        st.error(f"Failed to remove {entry.symbol}")
