"""
投資組合 AI 顧問

功能：
1. 自動讀取當前持倉（從資料庫）
2. 載入用戶研究報告（Markdown 檔案）
3. 抓取即時市場數據
4. AI 綜合分析：持倉風險、避險建議、調整策略
5. 具體執行建議（精確到口數、履約價）
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import TradingDatabase
from utils.ai_coach import AICoach
from utils.derivatives_support import InstrumentParser
from utils.option_market_data import OptionMarketData
from utils.styles import inject_custom_css, render_header_with_subtitle
from config.theme import COLORS

# 頁面配置
st.set_page_config(
    page_title="Portfolio AI 顧問 | AI Trading Journal",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS 樣式
inject_custom_css()

# 初始化
@st.cache_resource
def init_db():
    return TradingDatabase()

@st.cache_resource
def init_ai():
    try:
        return AICoach()
    except:
        return None

db = init_db()
ai_coach = init_ai()

render_header_with_subtitle(
    title="🧠 Portfolio AI 顧問",
    subtitle="基於實際持倉、市場走勢和研究報告，提供精準的風險管理與避險建議"
)

if ai_coach is None:
    st.error("⚠️ 需要設定 GEMINI_API_KEY")
    st.stop()

# ========== 1. 載入當前持倉 ==========
st.header("📊 當前持倉分析")

col1, col2 = st.columns([2, 1])

with col1:
    # 優先使用 Open Positions 快照
    latest_positions = db.get_latest_positions()

    if latest_positions:
        # 方案 A：使用 Open Positions（100% 準確）
        positions = pd.DataFrame(latest_positions)
        positions.rename(columns={'position': 'net_position', 'average_cost': 'avg_cost'}, inplace=True)

        st.success(f"✅ 使用 IBKR Open Positions 快照（{positions.iloc[0]['snapshot_date']}）")

        # 添加額外資訊顯示
        with st.expander("ℹ️ 持倉來源資訊"):
            st.info("""
            **使用 Open Positions 快照的優勢：**
            - ✅ 包含股票拆股/合股調整
            - ✅ 包含選擇權到期/指派事件
            - ✅ 包含代碼變更（如 FB → META）
            - ✅ 精確的平均成本與未實現損益

            **數據來源：** IBKR Flex Query
            """)
    else:
        # 方案 B：從交易推算（有風險）
        st.warning("⚠️ 未找到 Open Positions 快照，使用交易記錄推算（可能不含拆股/選擇權到期等事件）")

        trades = db.get_trades()

        if not trades:
            st.error("❌ 資料庫中沒有交易記錄或持倉快照，請先匯入數據")
            st.stop()

        # 轉換為 DataFrame
        df_trades = pd.DataFrame(trades)

        # 計算淨持倉
        def get_signed_quantity(row):
            action = row['action'].upper()
            qty = row['quantity']
            # 定義買入動作 (增加持倉)
            if action in ['BUY', 'BUY_TO_OPEN', 'BUY_TO_COVER', 'BOT']:
                return qty
            # 定義賣出動作 (減少持倉)
            elif action in ['SELL', 'SELL_TO_CLOSE', 'SELL_SHORT', 'SLD']:
                return -qty
            # 預設處理：如果是 BUY 開頭視為買入，否則視為賣出
            elif action.startswith('BUY'):
                return qty
            else:
                return -qty

        df_trades['signed_quantity'] = df_trades.apply(get_signed_quantity, axis=1)

        # 按標的分組計算淨部位
        positions = df_trades.groupby('symbol').agg({
            'signed_quantity': 'sum',
            'price': 'last',  # 最後交易價格
            'instrument_type': 'first',
            'underlying': 'first',
            'strike': 'first',
            'expiry': 'first',
            'option_type': 'first'
        }).reset_index()

        # 過濾出非零持倉
        positions = positions[positions['signed_quantity'] != 0].copy()
        positions.rename(columns={'signed_quantity': 'net_position'}, inplace=True)

    if len(positions) == 0:
        st.info("📭 當前沒有未平倉部位")
        st.stop()

    # 顯示持倉表格
    st.subheader("🎯 當前部位")

    display_cols = ['symbol', 'net_position', 'price', 'instrument_type']
    positions['value'] = positions['net_position'] * positions['price']

    st.dataframe(
        positions[display_cols + ['value']].rename(columns={
            'symbol': '標的',
            'net_position': '淨部位',
            'price': '最後成交價',
            'instrument_type': '類型',
            'value': '市值'
        }),
        use_container_width=True
    )

with col2:
    # 持倉統計
    total_value = positions['value'].sum()
    stock_positions = positions[positions['instrument_type'] == 'stock']
    option_positions = positions[positions['instrument_type'] == 'option']

    st.metric("總持倉市值", f"${total_value:,.2f}")
    st.metric("股票部位數", len(stock_positions))
    st.metric("選擇權部位數", len(option_positions))

# ========== 2. 載入研究報告 ==========
st.header("📝 研究報告")

# 建立 reports 資料夾（如果不存在）
reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

# 列出所有 Markdown 報告
report_files = list(reports_dir.glob("*.md"))

if not report_files:
    st.info("💡 提示：請在 `reports/` 資料夾中放入你的 Markdown 研究報告")
    reports_content = ""
else:
    selected_reports = st.multiselect(
        "選擇要納入分析的報告",
        options=[f.name for f in report_files],
        default=[f.name for f in report_files]  # 預設全選
    )

    if selected_reports:
        reports_content = ""
        for report_name in selected_reports:
            report_path = reports_dir / report_name
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                reports_content += f"\n\n## 報告：{report_name}\n\n{content}\n\n---\n"

        with st.expander("📄 查看已載入的報告內容", expanded=False):
            st.markdown(reports_content)
    else:
        reports_content = ""

# ========== 3. 抓取即時市場數據 ==========
st.header("📈 市場數據")

if st.button("🔄 更新所有持倉的即時數據", type="primary"):
    with st.spinner("載入中..."):
        market_data = {}

        for idx, row in positions.iterrows():
            symbol = row['symbol']
            underlying = row['underlying'] if pd.notna(row['underlying']) else symbol

            try:
                ticker = yf.Ticker(underlying)
                hist = ticker.history(period='5d')
                info = ticker.info

                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_close) / prev_close) * 100

                    market_data[symbol] = {
                        'current_price': current_price,
                        'change_pct': change_pct,
                        'volume': hist['Volume'].iloc[-1],
                        '52w_high': info.get('fiftyTwoWeekHigh', 'N/A'),
                        '52w_low': info.get('fiftyTwoWeekLow', 'N/A'),
                        'beta': info.get('beta', 'N/A')
                    }
            except Exception as e:
                st.warning(f"⚠️ 無法載入 {symbol} 的數據：{str(e)}")

        st.session_state.market_data = market_data
        st.success(f"✅ 成功載入 {len(market_data)} 個標的的市場數據")

# 顯示市場數據
if 'market_data' in st.session_state:
    st.subheader("💹 即時行情")

    market_df = pd.DataFrame(st.session_state.market_data).T
    market_df.index.name = '標的'

    # 強制轉換混合類型欄位為字串，避免 PyArrow 錯誤
    cols_to_stringify = ['52w_high', '52w_low', 'beta']
    for col in cols_to_stringify:
        if col in market_df.columns:
            market_df[col] = market_df[col].astype(str)

    st.dataframe(
        market_df.style.format({
            'current_price': lambda x: f'${x:.2f}' if isinstance(x, (int, float)) else str(x),
            'change_pct': lambda x: f'{x:+.2f}%' if isinstance(x, (int, float)) else str(x),
            'volume': lambda x: f'{x:,.0f}' if isinstance(x, (int, float)) else str(x),
            # 其他欄位已經轉為字串，不需要特別格式化，或者可以保留原樣
        }),
        use_container_width=True
    )

# ========== 3.5 選擇權市場分析 ==========
st.header("📊 選擇權市場分析")

# 篩選出選擇權部位
option_positions = positions[positions['instrument_type'].isin(['option', 'option_combo'])]

if len(option_positions) > 0 and 'market_data' in st.session_state:
    if st.button("🔍 分析選擇權市場數據", type="primary"):
        with st.spinner("正在抓取選擇權市場數據..."):
            option_analyzer = OptionMarketData()

            # 顯示數據源狀態
            st.info("📊 選擇權市場數據來源：yfinance（延遲15分鐘，僅限美股）")

            # 批次分析
            metrics = option_analyzer.get_portfolio_option_metrics(
                option_positions.to_dict('records')
            )

            if metrics['total_positions'] > 0:
                st.success(f"✅ 成功分析 {metrics['total_positions']} 個選擇權部位")

                # 顯示彙總指標
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均隱含波動率", f"{metrics['avg_iv']:.1f}%")
                with col2:
                    st.metric("總交易量", f"{metrics['total_volume']:,.0f}")
                with col3:
                    st.metric("總未平倉量", f"{metrics['total_open_interest']:,.0f}")

                # 顯示詳細數據表格
                st.subheader("📋 選擇權部位市場數據")

                details_df = pd.DataFrame(metrics['details'])

                st.dataframe(
                    details_df[[
                        'position_symbol', 'strike', 'type', 'expiry',
                        'volume', 'open_interest', 'implied_volatility',
                        'last_price'
                    ]].rename(columns={
                        'position_symbol': '部位',
                        'strike': '履約價',
                        'type': '類型',
                        'expiry': '到期日',
                        'volume': '交易量',
                        'open_interest': '未平倉量',
                        'implied_volatility': 'IV (%)',
                        'last_price': '最新價'
                    }).style.format({
                        '履約價': '${:.2f}',
                        'IV (%)': '{:.1f}%',
                        '交易量': '{:,.0f}',
                        '未平倉量': '{:,.0f}',
                        '最新價': '${:.2f}'
                    }),
                    use_container_width=True
                )

                # Put/Call Ratio 分析
                st.subheader("📈 市場情緒指標")

                unique_underlyings = option_positions['underlying'].unique()

                for underlying in unique_underlyings:
                    with st.expander(f"🎯 {underlying} Put/Call Ratio"):
                        pc_ratio = option_analyzer.calculate_put_call_ratio(underlying)

                        if 'error' not in pc_ratio:
                            col1, col2 = st.columns(2)

                            with col1:
                                st.metric("Volume Ratio (P/C)", f"{pc_ratio['volume_ratio']:.2f}")
                                st.caption(f"Put 交易量: {pc_ratio['put_volume']:,.0f}")
                                st.caption(f"Call 交易量: {pc_ratio['call_volume']:,.0f}")

                            with col2:
                                st.metric("OI Ratio (P/C)", f"{pc_ratio['oi_ratio']:.2f}")
                                st.caption(f"Put OI: {pc_ratio['put_oi']:,.0f}")
                                st.caption(f"Call OI: {pc_ratio['call_oi']:,.0f}")

                            # 情緒判斷
                            sentiment = pc_ratio['sentiment']
                            if "看跌" in sentiment:
                                st.warning(f"⚠️ 市場情緒：{sentiment}")
                            elif "看漲" in sentiment:
                                st.success(f"✅ 市場情緒：{sentiment}")
                            else:
                                st.info(f"ℹ️ 市場情緒：{sentiment}")
                        else:
                            st.error(f"無法取得 {underlying} 的數據")

                # 儲存到 session_state 供 AI 分析使用
                st.session_state.option_metrics = metrics
            else:
                st.warning("⚠️ 無法取得選擇權市場數據，可能是標的不支援或網路問題")
else:
    st.info("💡 持倉中無選擇權部位，或尚未載入市場數據")

# ========== 4. AI 綜合分析與建議 ==========
st.header("🤖 AI 綜合分析")

if st.button("🧠 開始 AI 深度分析", type="primary", use_container_width=True):
    if 'market_data' not in st.session_state:
        st.warning("⚠️ 請先更新市場數據")
        st.stop()

    with st.spinner("AI 分析中（這可能需要 30-60 秒）..."):
        # 準備完整的上下文資訊
        context = f"""
# 投資組合綜合分析請求

## 當前時間
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 當前持倉詳情
"""
        # 加入持倉資訊
        for idx, row in positions.iterrows():
            symbol = row['symbol']
            net_pos = row['net_position']
            pos_type = row['instrument_type']

            context += f"\n### {symbol}\n"
            context += f"- **類型**: {pos_type}\n"
            context += f"- **淨部位**: {net_pos:.0f} {'股' if pos_type == 'stock' else '口'}\n"
            context += f"- **成本價**: ${row['price']:.2f}\n"

            if symbol in st.session_state.market_data:
                mkt = st.session_state.market_data[symbol]
                context += f"- **現價**: ${mkt['current_price']:.2f}\n"
                context += f"- **日變化**: {mkt['change_pct']:+.2f}%\n"
                context += f"- **未實現損益**: ${(mkt['current_price'] - row['price']) * net_pos:,.2f}\n"

            if pos_type == 'option':
                context += f"- **履約價**: ${row['strike']}\n"
                context += f"- **到期日**: {row['expiry']}\n"
                context += f"- **類型**: {row['option_type']}\n"
            elif pos_type == 'option_combo':
                # 組合策略顯示
                context += f"- **策略類型**: {row.get('strategy_type', 'Custom Combo')}\n"
                context += f"- **履約價範圍**: ${row.get('strike_low', row['strike']):.2f} - ${row.get('strike_high', row['strike']):.2f}\n"
                context += f"- **到期日**: {row['expiry']}\n"
                context += f"- **⚠️ 這是組合策略避險部位，請將其視為整體評估風險**\n"

        # 加入市場數據
        context += "\n\n## 市場整體狀況\n"
        for symbol, data in st.session_state.market_data.items():
            context += f"- **{symbol}**: ${data['current_price']:.2f} ({data['change_pct']:+.2f}%), "
            context += f"52週範圍: ${data['52w_low']}-${data['52w_high']}, Beta: {data['beta']}\n"

        # 加入選擇權市場數據
        if 'option_metrics' in st.session_state:
            opt_metrics = st.session_state.option_metrics
            context += f"\n\n## 選擇權市場數據\n"
            context += f"- **持倉數量**: {opt_metrics['total_positions']} 個選擇權部位\n"
            context += f"- **平均隱含波動率**: {opt_metrics['avg_iv']:.1f}%\n"
            context += f"- **總交易量**: {opt_metrics['total_volume']:,.0f}\n"
            context += f"- **總未平倉量**: {opt_metrics['total_open_interest']:,.0f}\n\n"

            context += "### 各部位詳細數據：\n"
            for detail in opt_metrics['details']:
                context += f"- **{detail['position_symbol']}**: "
                context += f"Strike ${detail['strike']}, {detail['type']}, "
                context += f"IV {detail['implied_volatility']:.1f}%, "
                context += f"Volume {detail['volume']:,.0f}, OI {detail['open_interest']:,.0f}\n"

        # 加入研究報告
        if reports_content:
            context += f"\n\n## 用戶研究報告\n{reports_content}\n"

        # AI 提示詞
        prompt = f"""
你是一位資深投資組合經理和風險管理專家。請基於以下完整資訊，提供詳細的投資組合分析與建議：

{context}

**重要提示：**
- 如果持倉中包含「option_combo」類型（如 Risk Reversal、Iron Condor），這代表**已存在的組合策略避險部位**
- 請將這些組合策略視為**整體風險管理單元**，不要建議對已避險的部位再次避險
- 分析時需考慮組合策略的動態 Greeks（Delta、Gamma、Theta、Vega）
- 如果有提供選擇權市場數據（IV、交易量、未平倉量），請特別注意：
  - **高 IV（>60%）**：市場預期大幅波動，權利金昂貴
  - **低交易量 + 高未平倉量**：可能流動性不佳，難以平倉
  - **Put/Call Ratio > 1.2**：市場偏空，可能有下跌壓力

請提供以下分析（使用繁體中文，格式清晰）：

## 1. 投資組合風險評估
- 整體風險暴露分析（含組合策略的淨 Delta）
- 單一標的集中度風險
- 市場方向性風險（多空平衡）
- 時間風險（選擇權到期風險）
- 潛在損失情境分析（包含組合策略的保護範圍）
- **選擇權市場情緒分析**（若有數據）：
  - 當前 IV 水平的意義（高估或低估）
  - 交易量與未平倉量的警訊
  - 市場情緒偏多或偏空

## 2. 即時避險建議
**評估原則：**
- 若已存在組合策略避險單（如 Risk Reversal），先評估其保護效果
- 僅在保護不足時才建議額外避險

如果需要避險，請提供**具體可執行的建議**：
- 明確標的符號
- 精確口數/股數
- 建議履約價（選擇權）
- 建議到期日（選擇權）
- 執行時機建議

範例格式：
> **評估結果：** ONDS 已有 Risk Reversal（6.5/10）保護，覆蓋 XX 股，保護範圍為 $6.5-$10
> **建議：** 如股價跌破 $X，考慮加強下檔保護

## 3. 部位調整建議
- 是否需要減倉/加倉？
- 建議調整的標的與數量
- 調整的理由與時機

## 4. 基於研究報告的策略建議
（如果有提供研究報告）
- 報告觀點與當前持倉的一致性分析
- 根據報告建議的具體操作

## 5. 風險監控指標
- 需要密切關注的價格水平
- 停損/停利建議
- 預警觸發條件

請確保所有建議都是**具體、可執行、有數字**的，避免模糊的表述。
"""

        # 呼叫 AI
        response = ai_coach.chat(prompt)

        # 顯示結果
        st.markdown("### 🎯 AI 分析結果")
        st.markdown(response)

        # 儲存到 session_state
        st.session_state.last_analysis = response
        st.session_state.last_analysis_time = datetime.now()

# 顯示歷史分析
if 'last_analysis' in st.session_state:
    st.markdown("---")
    st.markdown(f"**上次分析時間**: {st.session_state.last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if st.button("📋 複製分析結果"):
        st.code(st.session_state.last_analysis)

# ========== 側邊欄：設定與說明 ==========
with st.sidebar:
    st.header("⚙️ 設定")

    st.markdown("### 📁 研究報告管理")
    st.info(f"""
    **報告資料夾**: `reports/`

    目前有 {len(report_files)} 份報告

    💡 將你的 Markdown 研究報告放入此資料夾，AI 會自動讀取分析
    """)

    st.markdown("---")

    st.markdown("### 🔄 更新頻率建議")
    st.markdown("""
    - **盤中**: 每 1-2 小時更新一次
    - **重大事件**: 立即更新分析
    - **每日收盤**: 完整檢視一次
    """)

    st.markdown("---")

    st.markdown("### 📊 使用說明")
    st.markdown("""
    1. 系統自動載入資料庫中的持倉
    2. 選擇要納入的研究報告
    3. 更新即時市場數據
    4. 執行 AI 綜合分析
    5. 根據建議執行操作
    """)
