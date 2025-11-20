"""
側邊欄觀察清單管理 UI 元件。

根據憲法原則 II (使用者控制的監控):
- 使用者擁有對觀察清單的完全控制權
- 僅限明確的新增/移除操作
"""

import streamlit as st
import sqlite3
from typing import Callable

from src.services.watchlist_service import add_symbol, remove_symbol, get_all_symbols


def render_watchlist_management(on_symbol_removed: Callable[[str], None] = None):
    """
    在側邊欄渲染觀察清單管理 UI。

    Args:
        on_symbol_removed: 當股票被移除時的可選回呼函式 (用於 UI 重新整理)

    UI 元件根據合約:
    - 股票輸入文字框
    - "加入觀察清單" 按鈕
    - 顯示目前股票與 X (移除) 按鈕
    - 透過 st.error/st.success/st.warning 顯示錯誤/成功訊息
    """
    st.sidebar.header("📊 觀察清單管理")

    # 輸入區塊
    with st.sidebar.form(key="add_symbol_form", clear_on_submit=True):
        symbol_input = st.text_input(
            "股票代碼",
            placeholder="例如: NVDA, AMD, TSLA",
            help="輸入股票代碼以加入您的觀察清單"
        )

        category_input = st.selectbox(
            "分類 (可選)",
            options=["", "Tech", "Core", "Speculative"],
            help="依分類組織股票 (可選)"
        )

        submit_button = st.form_submit_button("加入觀察清單")

        if submit_button and symbol_input:
            try:
                # 新增帶有可選分類的股票
                cat = category_input if category_input else None
                entry = add_symbol(symbol_input, category=cat)

                st.success(f"✅ 已將 {entry.symbol} 加入觀察清單")

            except sqlite3.IntegrityError:
                st.warning(f"⚠️ {symbol_input.upper()} 已在觀察清單中")

            except ValueError as e:
                st.error(f"❌ {str(e)}")

            except Exception as e:
                st.error(f"❌ 未預期的錯誤: {str(e)}")

    # 顯示目前觀察清單
    st.sidebar.divider()
    st.sidebar.subheader("目前觀察清單")

    watchlist = get_all_symbols()

    if not watchlist:
        st.sidebar.info("您的觀察清單是空的。請在上方新增股票以開始監控市場結構。")
    else:
        st.sidebar.caption(f"追蹤 {len(watchlist)} 檔股票")

        for entry in watchlist:
            col1, col2 = st.sidebar.columns([4, 1])

            with col1:
                # 顯示股票代碼，如果有分類則顯示分類徽章
                if entry.category:
                    st.write(f"**{entry.symbol}** `{entry.category}`")
                else:
                    st.write(f"**{entry.symbol}**")

            with col2:
                # 移除按鈕
                if st.button("✖", key=f"remove_{entry.symbol}", help=f"移除 {entry.symbol}"):
                    if remove_symbol(entry.symbol):
                        st.success(f"已移除 {entry.symbol}")

                        # 如果有提供回呼函式則觸發
                        if on_symbol_removed:
                            on_symbol_removed(entry.symbol)

                        # 強制重新執行以重新整理 UI
                        st.rerun()
                    else:
                        st.error(f"無法移除 {entry.symbol}")
