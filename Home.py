"""
AI 交易日誌系統 - 主頁面

系統入口與 CSV 檔案上傳功能
設計靈感：Bloomberg Terminal, TradingView, ThinkOrSwim
"""

import streamlit as st
import pandas as pd
from database import TradingDatabase
from datetime import datetime
from utils.derivatives_support import InstrumentParser
from utils.option_strategy_detector import OptionStrategyDetector
from utils.pnl_calculator import PnLCalculator
from utils.ai_coach import AICoach
from utils.styles import inject_custom_css, render_pnl_value, render_header_with_subtitle
from config.theme import COLORS, get_chart_layout_config
from pathlib import Path
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
import hashlib
import yfinance as yf

# 載入環境變數
load_dotenv()

# 初始化日誌系統
from utils.logging_config import setup_logging
import logging

setup_logging(log_level='INFO', log_file='trading_journal.log')
logger = logging.getLogger(__name__)

# 頁面配置 - 專業深色主題
st.set_page_config(
    page_title="AI Trading Journal | 智能交易日誌",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS 樣式
inject_custom_css()

# 初始化資料庫（確保資料庫已建立）
@st.cache_resource
def init_db():
    """初始化資料庫連接"""
    return TradingDatabase()

db = init_db()

# 每次會話開始時，強制執行一次 PnL 重算，確保數據正確
if 'initial_pnl_recalc' not in st.session_state:
    try:
        # 這裡不顯示 spinner，以免影響使用者體驗，但會在背景執行
        PnLCalculator(db).recalculate_all()
        st.session_state['initial_pnl_recalc'] = True
    except Exception as e:
        print(f"Initial PnL recalculation failed: {e}")


# 固定的 CSV 欄位對應
COLUMN_MAPPING = {
    'datetime': 'Date',
    'symbol': 'Symbol',
    'action': 'Side',
    'quantity': 'Quantity',
    'price': 'Price',
    'commission': 'Commission',
    'strike': 'Strike',
    'expiry': 'Expiry',
    'right': 'Right'
}

# --- 函數定義區 (Function Definitions) ---

def process_and_import_csv(df, source_name="CSV"):
    """處理並匯入 CSV 資料"""

    # 驗證必要欄位
    required_cols = [COLUMN_MAPPING['datetime'], COLUMN_MAPPING['symbol'],
                     COLUMN_MAPPING['action'], COLUMN_MAPPING['quantity'],
                     COLUMN_MAPPING['price']]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"❌ CSV 檔案缺少必要欄位：{', '.join(missing_cols)}")
        st.info(f"**必要欄位**：{', '.join(required_cols)}")
        return

    # 顯示處理中訊息
    st.toast(f"📊 正在處理 {len(df)} 筆交易記錄...")

    # 建立進度指示器
    progress_bar = st.progress(0)
    status_text = st.empty()

    new_count = 0
    duplicate_count = 0
    error_count = 0
    total = len(df)

    # 儲存所有處理後的交易（用於策略識別）
    all_trades = []

    for idx, row in df.iterrows():
        # 更新進度
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"處理中... {idx + 1}/{total} ({progress*100:.1f}%)")

        try:
            symbol = str(row[COLUMN_MAPPING['symbol']]).strip()
            action = str(row[COLUMN_MAPPING['action']]).strip().upper()

            # 處理選擇權欄位（如果存在）
            if COLUMN_MAPPING['strike'] in df.columns and not pd.isna(row.get(COLUMN_MAPPING['strike'])):
                strike = str(row[COLUMN_MAPPING['strike']]).strip()
                expiry = str(row.get(COLUMN_MAPPING['expiry'], '')).strip() if COLUMN_MAPPING['expiry'] in df.columns else ''
                right = str(row.get(COLUMN_MAPPING['right'], '')).strip() if COLUMN_MAPPING['right'] in df.columns else ''

                # 組合完整符號
                underlying = symbol.split()[0]
                if expiry and right:
                    # 清理到期日格式（移除重複的權利類型）
                    if right in expiry:
                        expiry = expiry.replace(right, '').strip()
                    symbol = f"{underlying} {expiry}{right}{strike}"

            # 解析標的類型
            parsed = InstrumentParser.parse_symbol(symbol)

            # 基本交易資料
            quantity = float(row[COLUMN_MAPPING['quantity']])
            price = float(row[COLUMN_MAPPING['price']])
            commission = float(row.get(COLUMN_MAPPING['commission'], 0)) if COLUMN_MAPPING['commission'] in df.columns and not pd.isna(row.get(COLUMN_MAPPING['commission'])) else 0

            # 初始化損益為 0（後續會自動計算）
            realized_pnl = 0

            # 構建交易資料
            trade_data = {
                'datetime': str(row[COLUMN_MAPPING['datetime']]),
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'commission': commission,
                'realized_pnl': realized_pnl,  # 先設為 0，後續計算
                'instrument_type': parsed['instrument_type'],
                'underlying': parsed['underlying'],
                'strike': parsed['strike'],
                'expiry': parsed['expiry'],
                'option_type': parsed['option_type'],
                'multiplier': parsed['multiplier']
            }

            # 儲存交易資料（用於策略識別）
            all_trades.append(trade_data)

            # 嘗試新增到資料庫
            if db.add_trade(trade_data):
                new_count += 1
            else:
                duplicate_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 3:  # 只顯示前 3 個錯誤
                st.warning(f"第 {idx + 1} 筆數據處理失敗：{str(e)}")

    # 清除進度指示
    progress_bar.empty()
    status_text.empty()
    
    # --- 觸發 PnL 重新計算 ---
    # 無論是否有新資料，都執行一次重算，以確保所有交易損益正確 (例如程式碼邏輯更新後)
    # if new_count > 0: (移除條件限制)
    status_text.text("🔄 正在重新計算已實現盈虧 (FIFO)...")
    pnl_calc = PnLCalculator(db)
    pnl_calc.recalculate_all()
    status_text.empty()
    if new_count > 0:
        st.toast("✅ 盈虧計算完成！")

    # 顯示結果
    st.toast(f"✅ 匯入完成！新增 {new_count} 筆，重複 {duplicate_count} 筆")

    if error_count > 0:
        st.warning(f"⚠️ 有 {error_count} 筆數據無法匯入，請檢查 CSV 格式")

    # 選擇權策略識別 (僅在手動上傳時顯示詳細識別結果，自動匯入模式下保持安靜)
    if source_name == "手動上傳":
        st.markdown("---")
        st.subheader("🎯 選擇權策略識別")

        with st.spinner("正在分析選擇權組合策略..."):
            strategies = OptionStrategyDetector.detect_strategies(all_trades, time_window_minutes=5)

        if strategies:
            st.success(f"✅ 識別出 {len(strategies)} 個選擇權策略組合")
        else:
            st.info("ℹ️ 未識別出標準選擇權策略組合。")


def render_dashboard(db):
    """渲染主儀表板 - 專業券商風格"""
    # 初始化 AI 教練
    try:
        ai_coach = AICoach()
        ai_provider_name = ai_coach.provider_name
    except Exception as e:
        st.sidebar.warning(f"AI 未啟用")
        ai_coach = None
        ai_provider_name = None

    # 1. 獲取數據
    stats = db.get_trade_statistics()
    pnl_by_symbol = db.get_pnl_by_symbol()
    trades = db.get_trades()
    
    if not trades:
        st.info("尚無交易數據，請先匯入 CSV 或同步 IBKR")
        return

    # ========== 主視覺區：大型累計盈虧曲線圖 ==========
    trades_df = pd.DataFrame(trades)
    trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])
    trades_df = trades_df.sort_values('datetime')
    trades_df['cumulative_pnl'] = trades_df['realized_pnl'].cumsum()
    
    total_pnl = stats.get('total_pnl', 0)
    win_rate = stats.get('win_rate', 0)
    total_trades = stats.get('total_trades', 0)
    
    # 計算日期範圍內的變化
    if len(trades_df) >= 2:
        first_pnl = trades_df['cumulative_pnl'].iloc[0]
        last_pnl = trades_df['cumulative_pnl'].iloc[-1]
        pnl_change = last_pnl - first_pnl
        pnl_change_pct = (pnl_change / abs(first_pnl) * 100) if first_pnl != 0 else 0
    else:
        pnl_change = total_pnl
        pnl_change_pct = 0
    
    # 主視覺：盈虧大數字 + 曲線圖
    pnl_color = COLORS.PROFIT if total_pnl >= 0 else COLORS.LOSS
    line_color = COLORS.PROFIT if total_pnl >= 0 else COLORS.LOSS
    fill_color = COLORS.PROFIT_BG if total_pnl >= 0 else COLORS.LOSS_BG
    
    # 頂部：總盈虧大數字（Robinhood 風格）
    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem 0;">
        <div style="font-size: 3rem; font-weight: bold; color: {pnl_color};">
            ${total_pnl:,.2f}
        </div>
        <div style="font-size: 1rem; color: {COLORS.TEXT_SECONDARY}; margin-top: 0.5rem;">
            總盈虧 
            <span style="color: {pnl_color};">
                {'▲' if total_pnl >= 0 else '▼'} {abs(pnl_change):,.0f} ({pnl_change_pct:+.1f}%)
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 大型累計盈虧曲線圖
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trades_df['datetime'],
        y=trades_df['cumulative_pnl'],
        mode='lines',
        name='累計盈虧',
        line=dict(color=line_color, width=3),
        fill='tozeroy',
        fillcolor=fill_color,
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>累計: $%{y:,.2f}<extra></extra>'
    ))
    
    # 添加零線
    fig.add_hline(y=0, line_color=COLORS.BORDER_ACCENT, line_width=1, opacity=0.5)
    
    # 標記峰值
    if len(trades_df) > 0:
        max_pnl = trades_df['cumulative_pnl'].max()
        max_idx = trades_df['cumulative_pnl'].idxmax()
        max_date = trades_df.loc[max_idx, 'datetime']
        
        fig.add_trace(go.Scatter(
            x=[max_date],
            y=[max_pnl],
            mode='markers',
            name='峰值',
            marker=dict(color=COLORS.PROFIT, size=10, symbol='circle'),
            hovertemplate=f'峰值: ${max_pnl:,.0f}<extra></extra>'
        ))
    
    layout_config = get_chart_layout_config('')
    # 覆蓋預設值
    layout_config['margin'] = dict(l=0, r=0, t=10, b=40)
    layout_config['xaxis'] = dict(
        showgrid=False,
        showline=False,
        tickfont=dict(color=COLORS.TEXT_MUTED)
    )
    layout_config['yaxis'] = dict(
        showgrid=True,
        gridcolor=COLORS.CHART_GRID,
        showline=False,
        tickfont=dict(color=COLORS.TEXT_MUTED),
        side='right',
        tickformat='$,.0f'
    )
    
    fig.update_layout(
        **layout_config,
        height=350,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # ========== KPI 指標卡片區 ==========
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_win = stats.get('avg_win', 0)
        st.metric("平均獲利", f"${avg_win:,.0f}", delta=None)
    
    with col2:
        avg_loss = stats.get('avg_loss', 0)
        st.metric("平均虧損", f"${avg_loss:,.0f}", delta=None)
    
    with col3:
        st.metric("勝率", f"{win_rate:.1f}%", delta=None)
    
    with col4:
        profit_factor = stats.get('profit_factor', 0)
        st.metric("獲利因子", f"{profit_factor:.2f}", delta=None)
    
    st.markdown("---")
    
    # ========== 持倉卡片區 ==========
    st.markdown("### 📊 核心標的動態")
    
    # 篩選模式選擇（改用下拉選單）
    col_filter, col_action = st.columns([3, 1])
    with col_filter:
        filter_mode = st.selectbox(
            "排序模式",
            ["🚀 最近交易", "💰 獲利最高", "💸 虧損最多", "🔥 交易最頻繁"],
            index=0
        )
    
    with col_action:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("⚡ 全局分析", help="一次分析所有持倉的點位建議", use_container_width=True):
            with st.spinner("正在批量分析所有持倉..."):
                try:
                    # 1. 準備數據
                    positions_data = []
                    # 使用所有有交易紀錄的標的進行分析，而不僅僅是篩選後的
                    symbols_to_fetch = list(pnl_by_symbol.keys())
                    
                    if not symbols_to_fetch:
                        st.warning("無持倉可分析")
                    else:
                        # 批量抓取數據
                        batch_data = yf.download(symbols_to_fetch, period="1mo", progress=False)
                        
                        for symbol in symbols_to_fetch:
                            # 計算持倉成本
                            symbol_trades = [t for t in trades if t['symbol'] == symbol]
                            buy_trades = [t for t in symbol_trades if t['action'] == 'BUY']
                            total_qty = sum(t['quantity'] for t in buy_trades)
                            total_cost = sum(t['quantity'] * t['price'] for t in buy_trades)
                            avg_cost = (total_cost / total_qty) if total_qty > 0 else 0
                            current_pos = sum(t['quantity'] if t['action'] == 'BUY' else -t['quantity'] for t in symbol_trades)
                            
                            # 獲取市場數據 (處理多層索引或單層索引)
                            try:
                                if len(symbols_to_fetch) == 1:
                                    closes = batch_data['Close']
                                else:
                                    closes = batch_data['Close'][symbol]
                                
                                current_price = closes.iloc[-1]
                                # 簡單趨勢描述
                                trend_str = f"Last 5 days: {closes.tail(5).tolist()}"
                                
                                positions_data.append({
                                    'symbol': symbol,
                                    'current_price': float(current_price),
                                    'avg_cost': float(avg_cost),
                                    'position_size': int(current_pos),
                                    'market_context': trend_str
                                })
                            except Exception as e:
                                print(f"Error processing {symbol}: {e}")
                        
                        # 2. 呼叫 AI
                        if positions_data:
                            batch_advice = ai_coach.get_batch_scaling_advice(positions_data)
                            
                            # 3. 存入 Session
                            for symbol, advice in batch_advice.items():
                                st.session_state[f"ai_scaling_{symbol}"] = advice
                            
                            st.success("✅ 分析完成！")
                            st.rerun()
                            
                except Exception as e:
                    st.error(f"批量分析失敗: {e}")
    
    # 準備基礎數據
    symbol_last_trade = {}
    symbol_trade_count = {}
    for t in trades:
        sym = t['symbol']
        dt = pd.to_datetime(t['datetime'])
        if sym not in symbol_last_trade or dt > symbol_last_trade[sym]:
            symbol_last_trade[sym] = dt
        symbol_trade_count[sym] = symbol_trade_count.get(sym, 0) + 1
            
    # 根據模式排序
    if "獲利最高" in filter_mode:
        # 按 PnL 降序
        sorted_items = sorted(pnl_by_symbol.items(), key=lambda x: x[1], reverse=True)
    elif "虧損最多" in filter_mode:
        # 按 PnL 升序
        sorted_items = sorted(pnl_by_symbol.items(), key=lambda x: x[1])
    elif "交易最頻繁" in filter_mode:
        # 按交易次數降序
        sorted_items = sorted(symbol_trade_count.items(), key=lambda x: x[1], reverse=True)
        # 轉換格式以匹配後續邏輯 (symbol, value) -> 我們只需要 symbol
        sorted_items = [(s, 0) for s, _ in sorted_items] # value 不重要，後續會重抓
    else: # 最近交易 (預設)
        sorted_items = sorted(symbol_last_trade.items(), key=lambda x: x[1], reverse=True)

    # 取前 4 名
    target_symbols = [item[0] for item in sorted_items[:4]]

    # 定義 dialog 函數 (必須在 loop 之前定義)
    @st.dialog(f"交易詳情", width="large")
    def show_trade_details(symbol, pnl, symbol_trades):
        # 計算統計
        win_count = sum(1 for t in symbol_trades if t['realized_pnl'] > 0)
        total_count = len(symbol_trades)
        win_rate = (win_count / total_count * 100) if total_count > 0 else 0
        
        # 標題區域
        col1, col2, col3 = st.columns(3)
        with col1:
            delta_color = "normal" if pnl >= 0 else "inverse"
            st.metric("總盈虧", f"${pnl:,.2f}", delta=f"{pnl:+,.0f}", delta_color=delta_color)
        with col2:
            st.metric("交易次數", total_count)
        with col3:
            st.metric("勝率", f"{win_rate:.1f}%", delta=f"{win_count}勝/{total_count-win_count}敗")
        
        st.divider()
        
        # 詳細交易記錄
        st.subheader("📋 交易記錄")
        symbol_df = pd.DataFrame(symbol_trades)
        symbol_df['datetime'] = pd.to_datetime(symbol_df['datetime'])
        symbol_df = symbol_df.sort_values('datetime', ascending=False)  # 最新的在最上面
        
        display_df = symbol_df[['datetime', 'action', 'quantity', 'price', 'realized_pnl']].copy()
        display_df.columns = ['日期時間', '動作', '數量', '價格', '已實現盈虧']
        
        st.dataframe(
            display_df.style.format({
                '價格': '${:.2f}',
                '已實現盈虧': '${:.2f}'
            }).background_gradient(subset=['已實現盈虧'], cmap='RdYlGn'),
            use_container_width=True,
            height=400
        )
    
    # 顯示卡片 (改為 2 欄佈局，使其更寬大)
    # 我們要顯示 4 張卡片，所以是 2x2 的網格
    
    # 定義卡片渲染邏輯 (閉包)
    def render_card_content(symbol, col):
        with col:
            # 使用 container(border=True) 創建卡片視覺
            with st.container(border=True):
                symbol_trades = [t for t in trades if t['symbol'] == symbol]
                pnl = pnl_by_symbol.get(symbol, 0)
                total_count = len(symbol_trades)
                
                # 獲取最後交易時間
                last_trade_time = symbol_last_trade.get(symbol, datetime.now())
                
                # 計算勝率
                win_count = sum(1 for t in symbol_trades if t['realized_pnl'] > 0)
                win_rate = (win_count / total_count * 100) if total_count > 0 else 0
                
                # 計算時間標籤
                days_diff = (datetime.now() - last_trade_time).days
                if days_diff == 0:
                    time_str = "Today"
                elif days_diff == 1:
                    time_str = "Yesterday"
                else:
                    time_str = last_trade_time.strftime('%m/%d')

                # 卡片頭部：標的 + 時間
                col_head1, col_head2 = st.columns([2, 1])
                with col_head1:
                    st.markdown(f"**{symbol}**")
                with col_head2:
                    st.caption(f"🕒 {time_str}")
                
                # 計算持倉數據
                buy_trades = [t for t in symbol_trades if t['action'].upper() in ['BUY', 'BOT']]
                sell_trades = [t for t in symbol_trades if t['action'].upper() in ['SELL', 'SLD']]
                
                total_buy_qty = sum(t['quantity'] for t in buy_trades)
                total_sell_qty = sum(t['quantity'] for t in sell_trades)
                current_position = total_buy_qty - total_sell_qty  # 目前持有股數
                
                # 計算平均成本
                total_cost = sum(t['quantity'] * t['price'] for t in buy_trades)
                avg_cost = (total_cost / total_buy_qty) if total_buy_qty > 0 else 0
                
                # 嘗試抓取即時價格
                current_price = None
                unrealized_pnl = 0
                unrealized_pnl_pct = 0
                market_value = 0
                
                try:
                    ticker_data = yf.Ticker(symbol)
                    hist = ticker_data.history(period="1d")
                    if len(hist) > 0:
                        current_price = hist['Close'].iloc[-1]
                        
                        if current_position > 0:
                            market_value = current_price * current_position
                            cost_basis = avg_cost * current_position
                            unrealized_pnl = market_value - cost_basis
                            unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
                except Exception:
                    pass  # 靜默處理，價格抓取失敗時顯示 N/A
                
                # 顯示當前價格
                if current_price:
                    price_str = f"${current_price:.2f}"
                    st.markdown(f"**Current Price:** {price_str}")
                else:
                    st.markdown("**Current Price:** N/A")
                
                # 持有股數 & 市值
                if current_position > 0:
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; color: {COLORS.TEXT_SECONDARY};">
                        持有股數 & 市值:<br>
                        <span style="color: {COLORS.TEXT_PRIMARY};">{current_position:.2f} shares</span>  
                        <span style="color: {COLORS.TEXT_MUTED};">${market_value:,.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 未實現損益
                    unrealized_color = COLORS.PROFIT if unrealized_pnl >= 0 else COLORS.LOSS
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; color: {COLORS.TEXT_SECONDARY};">
                        未實現損益:<br>
                        <span style="color: {unrealized_color}; font-weight: 600;">
                            ${unrealized_pnl:+,.2f} ({unrealized_pnl_pct:+.2f}%)
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("無持倉")
                
                # 已實現損益
                realized_color = COLORS.PROFIT if pnl >= 0 else COLORS.LOSS
                st.markdown(f"""
                <div style="font-size: 0.85rem; color: {COLORS.TEXT_SECONDARY}; margin-top: 0.5rem;">
                    已實現損益:<br>
                    <span style="color: {realized_color}; font-weight: 600; font-size: 1.1rem;">
                        ${pnl:,.2f}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                # 操作按鈕
                st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
                if st.button("📊 詳情", key=f"btn_{symbol}", use_container_width=True):
                    show_trade_details(symbol, pnl, symbol_trades)

    # 第一列
    cols1 = st.columns(2)
    for i in range(2):
        if i < len(target_symbols):
            render_card_content(target_symbols[i], cols1[i])
    
    # 第二列
    if len(target_symbols) > 2:
        cols2 = st.columns(2)
        for i in range(2):
            idx = i + 2
            if idx < len(target_symbols):
                render_card_content(target_symbols[idx], cols2[i])
    
    # ========== 持倉分布圓餅圖 ==========
    st.markdown("---")
    st.markdown("### 📊 持倉分布")
    
    # 計算各標的市值佔比（用於圓餅圖）
    position_values = {}
    for symbol in pnl_by_symbol.keys():
        symbol_trades_list = [t for t in trades if t['symbol'] == symbol]
        buy_trades = [t for t in symbol_trades_list if t['action'].upper() in ['BUY', 'BOT']]
        sell_trades = [t for t in symbol_trades_list if t['action'].upper() in ['SELL', 'SLD']]
        
        total_buy_qty = sum(t['quantity'] for t in buy_trades)
        total_sell_qty = sum(t['quantity'] for t in sell_trades)
        current_pos = total_buy_qty - total_sell_qty
        
        if current_pos > 0:
            # 用最後交易價格估算市值
            avg_price = sum(t['quantity'] * t['price'] for t in buy_trades) / total_buy_qty if total_buy_qty > 0 else 0
            position_values[symbol] = current_pos * avg_price
    
    if position_values:
        col_chart, col_list = st.columns([1, 1])
        
        with col_chart:
            # 圓餅圖
            fig_pie = go.Figure(data=[
                go.Pie(
                    labels=list(position_values.keys()),
                    values=list(position_values.values()),
                    hole=0.5,
                    marker=dict(
                        colors=[COLORS.CHART_LINE_PRIMARY, COLORS.CHART_LINE_SECONDARY, 
                                COLORS.WARNING, COLORS.PROFIT, COLORS.LOSS, '#8B5CF6', '#EC4899'],
                        line=dict(color=COLORS.BG_PRIMARY, width=2)
                    ),
                    textinfo='label+percent',
                    textfont=dict(size=11, color=COLORS.TEXT_PRIMARY),
                    hovertemplate='<b>%{label}</b><br>市值: $%{value:,.0f}<br>佔比: %{percent}<extra></extra>'
                )
            ])
            
            total_value = sum(position_values.values())
            
            layout_config = get_chart_layout_config('')
            # 覆蓋預設值
            layout_config['margin'] = dict(l=20, r=20, t=20, b=20)
            
            fig_pie.update_layout(
                **layout_config,
                height=300,
                showlegend=False,
                annotations=[
                    dict(
                        text=f'<b>${total_value:,.0f}</b><br>總市值',
                        x=0.5, y=0.5,
                        font=dict(size=16, color=COLORS.TEXT_PRIMARY),
                        showarrow=False
                    )
                ]
            )
            
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        
        with col_list:
            # 持倉列表
            st.markdown("**持有證券**")
            for symbol, value in sorted(position_values.items(), key=lambda x: x[1], reverse=True):
                pct = (value / total_value * 100) if total_value > 0 else 0
                pnl_val = pnl_by_symbol.get(symbol, 0)
                pnl_color = COLORS.PROFIT if pnl_val >= 0 else COLORS.LOSS
                
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 0.4rem 0; border-bottom: 1px solid {COLORS.BORDER_MUTED};">
                    <span style="color: {COLORS.TEXT_PRIMARY}; font-weight: 500;">{symbol}</span>
                    <span style="color: {COLORS.TEXT_SECONDARY};">${value:,.0f} ({pct:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("目前無持倉")

    # ========== 策略總覽區塊 ==========
    st.markdown("---")
    st.markdown("### 🎯 策略總覽")
    
    # 計算正股持倉
    stock_positions = {}
    for symbol in pnl_by_symbol.keys():
        # 檢查是否是正股（不含選擇權符號特徵）
        if ' ' not in symbol and not any(c.isdigit() for c in symbol[-4:]):
            symbol_trades_list = [t for t in trades if t['symbol'] == symbol]
            buy_qty = sum(t['quantity'] for t in symbol_trades_list if t['action'].upper() in ['BUY', 'BOT'])
            sell_qty = sum(t['quantity'] for t in symbol_trades_list if t['action'].upper() in ['SELL', 'SLD'])
            net_qty = buy_qty - sell_qty
            if net_qty > 0:
                stock_positions[symbol] = net_qty
    
    # 合成策略
    strategies = OptionStrategyDetector.synthesize_strategies_from_positions(trades, stock_positions)
    
    if strategies:
        # 按策略類型分組顯示
        strategy_cols = st.columns(min(len(strategies), 3))
        
        for idx, strategy in enumerate(strategies):
            col = strategy_cols[idx % 3]
            with col:
                with st.container(border=True):
                    # 策略標題
                    underlying = strategy['underlying']
                    strategy_name = strategy.get('strategy_name', '未識別')
                    
                    # 根據策略類型選擇顏色
                    if strategy['strategy_type'] in ['collar', 'protective_put']:
                        badge_color = COLORS.INFO  # 藍色 - 保護性策略
                    elif strategy['strategy_type'] in ['covered_call', 'short_put']:
                        badge_color = COLORS.WARNING  # 黃色 - 收益增強策略
                    elif strategy['strategy_type'] in ['naked_call']:
                        badge_color = COLORS.LOSS  # 紅色 - 高風險
                    else:
                        badge_color = COLORS.PROFIT  # 綠色 - 其他
                    
                    st.markdown(f"""
                    <div style="margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem; font-weight: 600; color: {COLORS.TEXT_PRIMARY};">{underlying}</span>
                        <span style="background: {badge_color}; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 8px;">
                            {strategy_name.split('（')[0]}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 策略說明
                    st.caption(strategy.get('description', ''))
                    
                    # 顯示組成部位
                    if strategy['has_stock']:
                        st.markdown(f"📈 **正股**: {strategy['stock_quantity']:.0f} 股")
                    
                    for opt in strategy.get('options', []):
                        action_icon = "🟢" if opt['action'] == 'LONG' else "🔴"
                        opt_type = "Call" if opt['option_type'] == 'C' else "Put"
                        action_text = "買" if opt['action'] == 'LONG' else "賣"
                        strike = opt.get('strike', 'N/A')
                        expiry = opt.get('expiry', 'N/A')
                        qty = abs(opt.get('quantity', 0))
                        
                        st.markdown(f"{action_icon} **{action_text} {opt_type}** @ ${strike} x {qty} (到期: {expiry})")
    else:
        st.info("未偵測到選擇權策略組合")
    
    st.markdown("---")
    
    # 3. 中間區域：資金曲線 (佔滿全寬)
    st.markdown("### 📈 累計盈虧曲線")
    
    # 修復：直接在前端計算資金曲線，不依賴 DB 方法
    if trades:
        df_trades = pd.DataFrame(trades)
        df_trades['datetime'] = pd.to_datetime(df_trades['datetime'])
        df_trades = df_trades.sort_values('datetime')
        df_trades['cumulative_pnl'] = df_trades['realized_pnl'].cumsum()
        
        # 繪製資金曲線 - 專業深色主題
        fig = go.Figure()
        
        # 判斷最終盈虧決定線條顏色
        final_pnl = df_trades['cumulative_pnl'].iloc[-1]
        line_color = COLORS.PROFIT if final_pnl >= 0 else COLORS.LOSS
        fill_color = COLORS.PROFIT_BG if final_pnl >= 0 else COLORS.LOSS_BG
        
        # 累計盈虧線
        fig.add_trace(go.Scatter(
            x=df_trades['datetime'],
            y=df_trades['cumulative_pnl'],
            mode='lines',
            name='累計盈虧',
            line=dict(color=line_color, width=3),
            fill='tozeroy',
            fillcolor=fill_color,
            hovertemplate='<b>日期</b>: %{x|%Y-%m-%d}<br><b>累計盈虧</b>: $%{y:,.2f}<extra></extra>'
        ))
        
        # 標記最高點
        max_pnl = df_trades['cumulative_pnl'].max()
        max_idx = df_trades['cumulative_pnl'].idxmax()
        max_date = df_trades.loc[max_idx, 'datetime']
        
        fig.add_trace(go.Scatter(
            x=[max_date],
            y=[max_pnl],
            mode='markers+text',
            name='最高點',
            marker=dict(color=COLORS.PROFIT, size=12, symbol='star', line=dict(width=2, color=COLORS.BG_PRIMARY)),
            text=[f'峰值 ${max_pnl:,.0f}'],
            textposition="top center",
            textfont=dict(color=COLORS.PROFIT, size=12, family="Inter"),
            hoverinfo='skip'
        ))
        
        # 標記最低點
        min_pnl = df_trades['cumulative_pnl'].min()
        min_idx = df_trades['cumulative_pnl'].idxmin()
        min_date = df_trades.loc[min_idx, 'datetime']
        
        if min_pnl < 0:
            fig.add_trace(go.Scatter(
                x=[min_date],
                y=[min_pnl],
                mode='markers+text',
                name='最低點',
                marker=dict(color=COLORS.LOSS, size=10, symbol='triangle-down', line=dict(width=2, color=COLORS.BG_PRIMARY)),
                text=[f'谷底 ${min_pnl:,.0f}'],
                textposition="bottom center",
                textfont=dict(color=COLORS.LOSS, size=11, family="Inter"),
                hoverinfo='skip'
            ))
        
        # 套用深色主題配置
        layout_config = get_chart_layout_config()
        # 覆蓋預設值
        layout_config['margin'] = dict(l=60, r=30, t=30, b=50)
        
        fig.update_layout(
            **layout_config,
            height=420,
            showlegend=False,
            yaxis_title="累計損益 ($)",
            yaxis_tickformat="$,.0f",
            xaxis_title=""
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("尚無足夠數據繪製資金曲線")
# --- 主程式區 (Main Execution) ---

# ========== IBKR Flex Query 設定 ==========
ibkr_token = os.getenv('IBKR_FLEX_TOKEN', '').strip()
ibkr_trades_query = os.getenv('IBKR_TRADES_QUERY_ID', '').strip()
ibkr_positions_query = os.getenv('IBKR_POSITIONS_QUERY_ID', '').strip()
ibkr_configured = bool(ibkr_token and ibkr_trades_query and ibkr_positions_query)


def perform_ibkr_sync():
    """執行 IBKR 同步"""
    try:
        from utils.ibkr_flex_query import IBKRFlexQuery
        
        with st.spinner("正在連接 IBKR..."):
            flex = IBKRFlexQuery()
            result = flex.sync_to_database(db)
            
            st.toast(f"✅ 同步完成！交易：{result['trades']} 筆，庫存：{result['positions']} 個部位")
            
            # 觸發 PnL 重算
            if result['trades'] > 0:
                pnl_calc = PnLCalculator(db)
                pnl_calc.recalculate_all()
            
            return True
    except ValueError as e:
        st.toast(f"❌ 設定錯誤：{str(e)}")
        return False
    except Exception as e:
        st.toast(f"❌ 同步失敗：{str(e)}")
        logger.error(f"IBKR Flex Query 同步失敗: {str(e)}")
        return False


# 自動同步（首次載入且有設定時）
if ibkr_configured:
    if 'ibkr_auto_synced' not in st.session_state:
        st.session_state['ibkr_auto_synced'] = False
    
    # 首次載入時自動同步
    if not st.session_state['ibkr_auto_synced']:
        if perform_ibkr_sync():
            st.session_state['ibkr_auto_synced'] = True
            st.rerun()
        else:
            st.session_state['ibkr_auto_synced'] = True  # 即使失敗也標記已嘗試

# 標題區域 + 右上角同步按鈕
col_title, col_sync = st.columns([6, 1])

with col_title:
    st.markdown(f"""
    <div style="margin-bottom: 0.5rem;">
        <span style="font-size: 1.8rem; font-weight: 700; color: {COLORS.TEXT_PRIMARY};">📊 AI Trading Journal</span>
        <p style="font-size: 0.9rem; color: {COLORS.TEXT_MUTED}; margin-top: 0.2rem;">
            智能交易日誌系統 | 由 AI 驅動的交易檢討與績效分析平台
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_sync:
    if ibkr_configured:
        if st.button("🔄", key="ibkr_sync_btn", help="從 IBKR 同步最新資料", use_container_width=True):
            perform_ibkr_sync()
            st.rerun()
    else:
        st.button("⚠️", key="ibkr_warn_btn", help="IBKR 未設定，請在 .env 設定 Token 和 Query ID", disabled=True, use_container_width=True)

# 檢查自動匯入設定 (優先使用 Google Sheet URL)
google_sheet_url = os.getenv('GOOGLE_SHEET_URL', '').strip()
auto_csv_path = os.getenv('AUTO_IMPORT_CSV_PATH', '').strip()

# 決定匯入來源
import_source = None
source_type = None

if google_sheet_url:
    import_source = google_sheet_url
    source_type = 'url'
elif auto_csv_path and Path(auto_csv_path).exists():
    import_source = auto_csv_path
    source_type = 'local'

# 自動載入模式
if import_source:
    # 儀表板標題
    st.markdown("## 📝 交易紀錄")

    # 狀態列 (Status Bar)
    status_col1, status_col2 = st.columns([3, 1])
    with status_col1:
        if source_type == 'url':
            st.caption(f"📡 自動匯入來源: Google Sheet (雲端連結)")
        else:
            st.caption(f"📡 自動匯入來源: `{import_source}`")
            
    with status_col2:
        # 手動重載按鈕 (小型化)
        if st.button("🔄 重新整理", type="secondary", use_container_width=True):
            st.session_state['last_import_time'] = 0 # 強制觸發更新
            st.rerun()

    # 檢查是否需要自動載入（基於內容 hash，避免重複匯入）
    should_auto_load = False
    current_time = datetime.now().timestamp()
    last_import_time = st.session_state.get('last_import_time', 0)
    last_content_hash = st.session_state.get('last_content_hash', '')

    # 計算當前內容 hash
    try:
        df_preview = pd.read_csv(import_source)
        # 使用前 1000 行的內容生成 hash（避免大檔案效能問題）
        content_sample = df_preview.head(1000).to_csv(index=False)
        current_content_hash = hashlib.md5(content_sample.encode()).hexdigest()

        # 比較 hash，只有內容改變才重新匯入
        if current_content_hash != last_content_hash:
            should_auto_load = True
            st.session_state['last_content_hash'] = current_content_hash
            st.session_state['last_import_time'] = current_time
    except Exception as e:
        st.warning(f"無法讀取資料來源：{str(e)}")
    
    # 執行載入邏輯
    if should_auto_load:
        try:
            # 使用已經讀取的 df_preview
            if 'df_preview' in locals() and len(df_preview) > 0:
                with st.spinner(f"檢測到新資料，正在匯入..."):
                    process_and_import_csv(df_preview, source_name="自動載入")
        except Exception as e:
            st.error(f"❌ 自動匯入失敗：{str(e)}")
    else:
        # 顯示已同步訊息
        if last_content_hash:
            st.caption("✅ 資料已是最新，無需重新匯入")
    
    # 渲染儀表板
    render_dashboard(db)

    st.markdown("---")
    # 顯示詳細數據開關
    with st.expander("📂 查看原始檔案詳情與數據"):
        col1, col2, col3 = st.columns(3)
        with col1:
            if source_type == 'url':
                st.metric("來源類型", "Google Sheet")
            else:
                st.metric("檔案名稱", Path(import_source).name)
        with col2:
            if source_type == 'local':
                file_size_mb = Path(import_source).stat().st_size / 1024 / 1024
                st.metric("檔案大小", f"{file_size_mb:.2f} MB")
            else:
                st.metric("連線狀態", "線上")
        with col3:
            if source_type == 'local':
                mod_time = datetime.fromtimestamp(Path(import_source).stat().st_mtime)
                st.metric("檔案最後更新", mod_time.strftime('%Y-%m-%d %H:%M'))
            else:
                update_time = datetime.fromtimestamp(st.session_state.get('last_import_time', 0))
                st.metric("上次同步時間", update_time.strftime('%Y-%m-%d %H:%M'))
            
        if should_auto_load and 'df' in locals() and len(df) > 0:
             st.dataframe(df.head(10), use_container_width=True)

# 手動上傳模式
else:
    # 先檢查資料庫中是否有交易數據，有則顯示儀表板
    existing_trades = db.get_trades()
    if existing_trades:
        # 顯示儀表板
        render_dashboard(db)
        st.markdown("---")
    
    # 上傳區域（放在 expander 中）
    with st.expander("📤 上傳交易報表", expanded=not existing_trades):
        st.caption(f"支援欄位：`{COLUMN_MAPPING['datetime']}`、`{COLUMN_MAPPING['symbol']}`、`{COLUMN_MAPPING['action']}`、`{COLUMN_MAPPING['quantity']}`、`{COLUMN_MAPPING['price']}`")

        uploaded_file = st.file_uploader(
            "選擇 CSV 檔案",
            type=['csv'],
            help="請選擇從 IBKR 下載的交易報表 CSV 檔案，或 n8n 自動生成的匯總報表"
        )

        if uploaded_file is not None:
            try:
                # 讀取 CSV
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ 成功讀取檔案，共 {len(df)} 筆交易紀錄")

                # 資料驗證
                if len(df) == 0:
                    st.error("❌ CSV 檔案是空的，請檢查檔案內容")
                    st.stop()

                # 顯示預覽
                with st.expander("📋 查看原始數據（前 10 筆）", expanded=False):
                    st.dataframe(df.head(10), use_container_width=True)

                # 直接處理並匯入
                process_and_import_csv(df, source_name="手動上傳")

            except Exception as e:
                st.error(f"❌ 檔案處理錯誤：{str(e)}")
                st.info("請確認 CSV 檔案格式正確，或聯繫技術支援。")

    # ========== Open Positions 匯入 ==========
    st.markdown("---")
    st.header("📊 匯入 Open Positions（未平倉快照）")

    st.info("""
    **Open Positions 快照的用途：**
    - ✅ 提供 100% 準確的持倉資訊
    - ✅ 包含股票拆股、選擇權到期等事件
    - ✅ 精確的平均成本與未實現損益

    **CSV 格式要求：**
    - 必須包含欄位：`Symbol`, `Position`, `Mark Price`, `Average Cost`
    - 可選欄位：`Unrealized P&L`, `Strike`, `Expiry`, `Right`

    💡 **提示**：從 IBKR Flex Query 匯出 Open Positions 報表
    """)

    uploaded_positions = st.file_uploader(
        "選擇 Open Positions CSV",
        type=['csv'],
        key="positions_uploader",
        help="請選擇從 IBKR 匯出的 Open Positions 報表"
    )

    if uploaded_positions is not None:
        try:
            df_pos = pd.read_csv(uploaded_positions)
            st.success(f"✅ 成功讀取 Open Positions，共 {len(df_pos)} 個部位")

            # 驗證欄位
            required_cols = ['Symbol', 'Position', 'Mark Price', 'Average Cost']
            missing_cols = [col for col in required_cols if col not in df_pos.columns]

            if missing_cols:
                st.error(f"❌ 缺少必要欄位：{', '.join(missing_cols)}")
                st.stop()

            # 顯示預覽
            with st.expander("📋 查看 Open Positions 數據", expanded=True):
                st.dataframe(df_pos.head(10), use_container_width=True)

            # 轉換為資料庫格式
            positions_data = []
            for _, row in df_pos.iterrows():
                pos_dict = {
                    'symbol': str(row['Symbol']).strip(),
                    'position': float(row['Position']),
                    'mark_price': float(row['Mark Price']) if pd.notna(row.get('Mark Price')) else None,
                    'average_cost': float(row['Average Cost']) if pd.notna(row.get('Average Cost')) else None,
                    'unrealized_pnl': float(row.get('Unrealized P&L', 0)) if pd.notna(row.get('Unrealized P&L')) else 0
                }
                positions_data.append(pos_dict)

            # 寫入資料庫
            if st.button("💾 匯入 Open Positions", type="primary", use_container_width=True):
                with st.spinner("正在匯入..."):
                    count = db.upsert_open_positions(positions_data)
                st.success(f"✅ 成功匯入 {count} 個持倉快照！")
                st.info("請前往 **Portfolio Advisor** 頁面查看分析結果")

        except Exception as e:
            st.error(f"❌ 檔案處理錯誤：{str(e)}")
            st.info("請確認 CSV 格式正確")

# 側邊欄：系統狀態 - 專業控制面板
with st.sidebar:
    # Logo 區域
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0; border-bottom: 1px solid {COLORS.BORDER_MUTED}; margin-bottom: 1rem;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
        <div style="font-size: 1rem; font-weight: 600; color: {COLORS.TEXT_PRIMARY};">AI Trading Journal</div>
        <div style="font-size: 0.75rem; color: {COLORS.TEXT_MUTED};">v2.0 Professional</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📈 帳戶總覽")

    # 顯示資料庫統計
    stats = db.get_trade_statistics()
    symbols = db.get_all_symbols()
    
    total_pnl = stats.get('total_pnl', 0)
    pnl_color = COLORS.PROFIT if total_pnl >= 0 else COLORS.LOSS
    
    # 主要盈虧指標 - 大字顯示
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {COLORS.BG_SECONDARY} 0%, {COLORS.BG_TERTIARY} 100%);
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        text-align: center;
    ">
        <div style="font-size: 0.75rem; color: {COLORS.TEXT_MUTED}; text-transform: uppercase; letter-spacing: 1px;">總盈虧</div>
        <div style="font-size: 1.75rem; font-weight: 700; color: {pnl_color}; font-family: 'SF Mono', monospace;">
            {'+'if total_pnl >= 0 else ''}${total_pnl:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 次要指標
    col1, col2 = st.columns(2)
    with col1:
        st.metric("交易筆數", stats.get('total_trades', 0))
    with col2:
        st.metric("標的數量", len(symbols))

    # 自動檢查是否需要重算 PnL (若有交易但總盈虧為 0)
    if stats.get('total_trades', 0) > 0 and stats.get('total_pnl', 0) == 0:
        if 'pnl_recalc_done' not in st.session_state:
            st.toast("🔄 檢測到盈虧數據未初始化，正在重新計算...")
            pnl_calc = PnLCalculator(db)
            pnl_calc.recalculate_all()
            st.session_state['pnl_recalc_done'] = True
            st.rerun()

    st.markdown("---")
    
    # 快速導航 - 專業樣式
    st.markdown("### 🧭 功能導航")
    
    nav_items = [
        ("📈", "交易檢討", "1_Review"),
        ("🎯", "策略模擬", "2_Strategy"),
        ("📊", "績效成績單", "3_Report_Card"),
        ("🔬", "策略回測", "4_Strategy_Lab"),
        ("💡", "選擇權顧問", "5_Options_Strategy"),
        ("🤖", "Portfolio AI", "6_Portfolio_Advisor"),
        ("🃏", "錯誤卡片", "7_Mistake_Cards"),
    ]
    
    for icon, label, page in nav_items:
        st.page_link(f"pages/{page}.py", label=f"{icon} {label}", use_container_width=True)
    
    st.markdown("---")
    
    # 手動維護工具
    with st.expander("🔧 系統維護", expanded=False):
        if st.button("🔄 重算盈虧", use_container_width=True, help="使用 FIFO 方法重新計算所有交易的已實現盈虧"):
            with st.spinner("正在重新計算..."):
                pnl_calc = PnLCalculator(db)
                pnl_calc.recalculate_all()
            st.success("✅ 完成")
            st.rerun()
        
        if st.button("🗑️ 清空資料庫", type="secondary", use_container_width=True):
            if db.clear_database():
                st.success("✅ 資料庫已清空")
                st.rerun()

    # 底部資訊
    st.markdown(f"""
    <div style="
        position: fixed;
        bottom: 0;
        left: 0;
        width: var(--sidebar-width);
        padding: 0.75rem 1rem;
        background: {COLORS.BG_SECONDARY};
        border-top: 1px solid {COLORS.BORDER_MUTED};
        font-size: 0.7rem;
        color: {COLORS.TEXT_MUTED};
    ">
        <div>💡 <strong>提示</strong>: 上傳交易報表後自動匯入資料</div>
        <div style="margin-top: 0.25rem;">⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

