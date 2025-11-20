"""
GEX Sentinel 觀察清單儀表板 - 主 Streamlit 頁面

功能: 001-gex-sentinel-watchlist
使用者故事: P1 (觀察清單管理), P2 (掃描器), P3 (深入分析), P4 (分類)
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

# 頁面配置
st.set_page_config(
    page_title="GEX Sentinel | AI Trading Coach",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 首次執行時初始化資料庫
initialize_db()

# 標題
st.title("📊 GEX Sentinel 觀察清單儀表板")
st.caption("使用者管理的觀察清單，具備批次 GEX/Max Pain 計算與深入結構分析功能")

# --- 側邊欄觀察清單管理 (使用者故事 1 - P1 MVP) ---
def on_symbol_removed(symbol: str):
    """當股票代碼被移除時的回呼函式 - 重新整理主畫面"""
    st.cache_data.clear()
    st.rerun()

render_watchlist_management(on_symbol_removed=on_symbol_removed)

# 新增重新整理按鈕至側邊欄 (T072)
st.sidebar.divider()
if st.sidebar.button("🔄 重新整理數據", help="清除快取並重新載入所有數據"):
    st.cache_data.clear()
    st.rerun()

# --- 數據獲取與處理 ---

@st.cache_data(ttl=300)
def fetch_symbol_data(symbol: str):
    """獲取單一股票的所有數據，並包含錯誤處理。"""
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
    """獲取觀察清單中所有股票的數據，並顯示進度條。"""
    results = {}
    if not watchlist:
        return results
        
    progress_bar = st.progress(0, text="正在初始化批次獲取...")
    
    for i, entry in enumerate(watchlist):
        progress_bar.progress((i + 1) / len(watchlist), text=f"正在分析 {entry.symbol}...")
        results[entry.symbol] = fetch_symbol_data(entry.symbol)
    
    progress_bar.empty()
    return results

# --- UI 元件 ---

def render_scanner_table(watchlist, data_map):
    """渲染使用者故事 2: 掃描器表格視圖。"""
    st.subheader("📡 市場掃描器")
    
    table_data = []
    for entry in watchlist:
        symbol = entry.symbol
        data = data_map.get(symbol)
        
        if not data or data["status"] == "error":
            table_data.append({
                "Symbol": symbol,
                "Price": "Error",
                "Change": "---",
                "GEX State": "⚠️ 數據不可用",
                "Max Pain": "---",
                "Walls (Call/Put)": "---",
                "Category": entry.category or "—"
            })
            continue
            
        price: MarketSnapshot = data["price"]
        gex: GEXProfile = data["gex"]
        
        # 格式化價格變動
        change_str = f"{price.change_pct:+.2f}%"
        
        # 格式化 Max Pain 距離
        if gex.max_pain:
            dist_pct = ((gex.max_pain - price.current_price) / price.current_price) * 100
            mp_str = f"${gex.max_pain:.2f} ({dist_pct:+.1f}%)"
        else:
            mp_str = "N/A"
            
        # 格式化牆
        walls_str = f"C: ${gex.call_wall} / P: ${gex.put_wall}" if (gex.call_wall and gex.put_wall) else "N/A"
        
        # GEX 狀態徽章
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
            "_raw_change": price.change_pct  # 隱藏欄位，若需要可用於樣式設定
        })
        
    if not table_data:
        return

    df = pd.DataFrame(table_data)
    
    # 設定 dataframe 樣式
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
    """渲染使用者故事 3: 深入分析。"""
    st.divider()
    st.header(f"🔍 深入分析: {symbol}")
    
    if data["status"] == "error":
        st.error(f"無法載入 {symbol} 的分析: {data['error']}")
        return

    price: MarketSnapshot = data["price"]
    gex: GEXProfile = data["gex"]
    sent: SentimentIndicators = data["sentiment"]
    
    # --- 頂層指標 ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("當前價格", f"${price.current_price:.2f}", f"{price.change_pct:+.2f}%")
    col2.metric("淨 GEX", f"${gex.net_gex / 1_000_000_000:.2f}B", delta_color="off")
    col3.metric("RSI (14)", f"{sent.rsi:.1f}")
    col4.metric("IV 百分位數", f"{sent.iv_percentile:.0f}%")
    
    # --- 結構卡片 ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("🏰 GEX 牆與水平")
        st.info(f"""
        **Call 牆 (壓力):** ${gex.call_wall}
        
        **Max Pain (磁鐵):** ${gex.max_pain}
        
        **Put 牆 (支撐):** ${gex.put_wall}
        """)
    
    with c2:
        st.subheader("🌡️ 情緒與部位")
        pcr_delta = "中性"
        if sent.pcr > 1.0: pcr_delta = "看跌 (Put 多)"
        elif sent.pcr < 0.7: pcr_delta = "看漲 (Call 多)"
        
        st.success(f"""
        **Put/Call 比率:** {sent.pcr:.2f} ({pcr_delta})
        
        **GEX 狀態:** {gex.gex_state}
        
        **波動率:** IV Rank 為 52 週範圍的 {sent.iv_percentile:.0f}%
        """)

    # --- AI 分析 ---
    st.subheader("🤖 AI 結構分析師")
    
    if "ai_analysis_cache" not in st.session_state:
        st.session_state.ai_analysis_cache = {}
        
    cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H')}"
    
    if st.button(f"為 {symbol} 產生分析", type="primary"):
        with st.spinner("正在諮詢 AI 分析師..."):
            try:
                if cache_key in st.session_state.ai_analysis_cache:
                    analysis = st.session_state.ai_analysis_cache[cache_key]
                else:
                    analysis = generate_structure_analysis(symbol, gex, sent)
                    st.session_state.ai_analysis_cache[cache_key] = analysis
                
                st.markdown(analysis)
            except Exception as e:
                st.error(f"分析產生失敗: {e}")

# --- 主要執行流程 ---

st.divider()

# 獲取當前觀察清單
watchlist = get_all_symbols()

if not watchlist:
    # 空狀態
    st.info("""
    ### 👋 歡迎來到 GEX Sentinel!
    您的觀察清單是空的。請在側邊欄新增股票以開始監控市場結構。
    """)
else:
    # 1. 批次獲取數據
    data_map = fetch_batch_data(watchlist)
    
    # 2. 渲染掃描器表格
    render_scanner_table(watchlist, data_map)
    
    # 3. 檢查選擇
    selection = st.session_state.get("scanner_selection")
    if selection and selection["selection"]["rows"]:
        selected_idx = selection["selection"]["rows"][0]
        if selected_idx < len(watchlist):
            selected_symbol = watchlist[selected_idx].symbol
            
            # 4. 渲染深入分析
            if selected_symbol in data_map:
                render_deep_dive(selected_symbol, data_map[selected_symbol])

# 頁尾
st.divider()
st.caption("Built with ❤️ | 憲法原則: 隱私優先 | 透過快取提升效能 | 結構優於價格")
