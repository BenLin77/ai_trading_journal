"""
策略實驗室頁面 (Strategy Module)

功能：
1. 輸入當前持倉情境（股票/選擇權/期貨）
2. 抓取即時市場數據（價格、IV）
3. Python 策略引擎推薦
4. AI 深度策略分析
"""

import streamlit as st
import yfinance as yf
from utils.ai_coach import AICoach
from utils.derivatives_support import InstrumentParser
from utils.styles import inject_custom_css, render_header_with_subtitle
from config.theme import COLORS
from datetime import datetime

# 頁面配置
st.set_page_config(
    page_title="策略實驗室 | AI Trading Journal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS 樣式
inject_custom_css()

# 初始化 AI
@st.cache_resource
def init_ai():
    """初始化 AI 教練"""
    try:
        return AICoach()
    except ValueError:
        return None

ai_coach = init_ai()

# 頁面標題
render_header_with_subtitle(
    title="🎯 策略實驗室",
    subtitle="What-if 情境分析與股票/選擇權/期貨策略建議"
)

# 警告
if ai_coach is None:
    st.warning("⚠️ 未偵測到 GEMINI_API_KEY，AI 策略建議功能將無法使用。")

# 左側：輸入區
with st.sidebar:
    st.header("📋 情境設定")

    # 資產類型選擇
    asset_type = st.radio(
        "資產類型",
        ["股票", "選擇權", "期貨"],
        horizontal=True,
        help="選擇你要分析的資產類型"
    )

    # 標的輸入
    if asset_type == "股票":
        symbol = st.text_input(
            "標的代號",
            value="AAPL",
            help="輸入股票代號，例如 AAPL、TSLA"
        ).upper()
        parsed_symbol = InstrumentParser.parse_symbol(symbol)

    elif asset_type == "選擇權":
        st.markdown("**選擇權資訊**")
        underlying = st.text_input("標的股票", value="AAPL", help="標的股票代號").upper()
        expiry = st.date_input("到期日", help="選擇權到期日")
        strike = st.number_input("Strike Price", min_value=0.0, value=150.0, step=5.0)
        option_type = st.selectbox("類型", ["Call", "Put"])

        # 組合成選擇權代號
        symbol = f"{underlying} {expiry.strftime('%Y-%m-%d')} {strike} {option_type}"
        parsed_symbol = InstrumentParser.parse_symbol(symbol)

    else:  # 期貨
        st.markdown("**期貨資訊**")
        futures_underlying = st.selectbox(
            "期貨標的",
            ["ES", "NQ", "YM", "CL", "GC", "SI"],
            help="選擇期貨標的"
        )
        month_mapping = {
            'F': '1月', 'G': '2月', 'H': '3月', 'J': '4月',
            'K': '5月', 'M': '6月', 'N': '7月', 'Q': '8月',
            'U': '9月', 'V': '10月', 'X': '11月', 'Z': '12月'
        }
        month_code = st.selectbox(
            "到期月份",
            month_mapping,
            format_func=lambda x: f"{x} ({month_mapping[x]})"
        )
        year = st.selectbox("年份", ["24", "25", "26"])

        symbol = f"{futures_underlying}{month_code}{year}"
        parsed_symbol = InstrumentParser.parse_symbol(symbol)

    # 抓取即時數據按鈕
    if st.button("📡 抓取即時數據", type="primary"):
        # 對於選擇權和期貨，使用 underlying symbol 抓取數據
        fetch_symbol = parsed_symbol['underlying']

        with st.spinner(f"正在抓取 {fetch_symbol} 的即時數據..."):
            try:
                ticker = yf.Ticker(fetch_symbol)
                info = ticker.info

                # 取得當前價格
                current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0

                # 取得 IV（如果可用）
                iv_30 = info.get('impliedVolatility', 0) * 100 if info.get('impliedVolatility') else None

                # 儲存到 session state
                st.session_state['current_price'] = current_price
                st.session_state['iv_30'] = iv_30
                st.session_state['asset_type'] = asset_type
                st.session_state['parsed_symbol'] = parsed_symbol

                st.success(f"✅ 成功抓取 {fetch_symbol} 的數據")

            except Exception as e:
                st.error(f"抓取數據失敗：{str(e)}")

# 主要內容區
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("💼 持倉資訊")

    # 根據資產類型調整標籤
    if asset_type == "股票":
        quantity_label = "持股數"
        quantity_help = "你目前持有多少股"
    elif asset_type == "選擇權":
        quantity_label = "合約數"
        quantity_help = "你目前持有多少口選擇權（1口 = 100股）"
    else:  # 期貨
        quantity_label = "合約數"
        quantity_help = "你目前持有多少口期貨"

    quantity = st.number_input(
        quantity_label,
        min_value=0,
        value=1 if asset_type != "股票" else 100,
        step=1 if asset_type != "股票" else 10,
        help=quantity_help
    )

    avg_cost = st.number_input(
        "平均成本 ($)",
        min_value=0.0,
        value=100.0 if asset_type == "股票" else 5.0,
        step=1.0 if asset_type == "股票" else 0.1,
        help="你的平均買入成本"
    )

with col2:
    st.subheader("📊 市場數據")

    current_price = st.number_input(
        "當前市價 ($)",
        min_value=0.0,
        value=st.session_state.get('current_price', 100.0),
        step=0.1,
        help="當前股價（可自動抓取或手動輸入）"
    )

    iv_30 = st.number_input(
        "30 天 IV (%)",
        min_value=0.0,
        max_value=200.0,
        value=st.session_state.get('iv_30', 30.0) if st.session_state.get('iv_30') else 30.0,
        step=1.0,
        help="30 天隱含波動率（百分比）"
    )

# 計算當前浮動盈虧（考慮合約倍數）
multiplier = parsed_symbol.get('multiplier', 1)
notional_value = current_price * quantity * multiplier
unrealized_pnl = (current_price - avg_cost) * quantity * multiplier
pnl_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

st.markdown("---")

# 顯示資產類型資訊
if asset_type != "股票":
    st.info(f"📊 {asset_type}：{symbol} (倍數: {multiplier})")

col1, col2, col3 = st.columns(3)
col1.metric("持倉市值", f"${notional_value:,.2f}")
col2.metric("浮動盈虧", f"${unrealized_pnl:,.2f}", f"{pnl_pct:+.2f}%")
col3.metric("IV 水平", f"{iv_30:.1f}%")

# 情境輸入
st.markdown("---")
st.subheader("🎯 情境分析")

col1, col2 = st.columns(2)

with col1:
    upcoming_events = st.text_area(
        "即將發生的事件",
        placeholder="例如：本週三財報、下週 FOMC 會議",
        height=100,
        help="影響股價的重要事件"
    )

with col2:
    # 根據資產類型調整目標選項
    if asset_type == "股票":
        goal_options = [
            "鎖定當前利潤",
            "產生現金流（收權利金）",
            "降低持倉成本",
            "保護下檔風險",
            "增加上檔曝險"
        ]
    elif asset_type == "選擇權":
        goal_options = [
            "獲利了結",
            "調整部位（Roll）",
            "加碼部位",
            "對沖風險",
            "策略轉換"
        ]
    else:  # 期貨
        goal_options = [
            "平倉出場",
            "換月（Roll Over）",
            "加碼部位",
            "對沖風險",
            "價差交易（Spread）"
        ]

    goal = st.selectbox(
        "我的主要目標",
        goal_options,
        help="選擇你的主要目標"
    )

# Python 策略引擎（簡單規則）
def recommend_strategies(goal: str, iv: float, asset_type: str) -> list:
    """
    基於目標、IV 和資產類型推薦策略

    Args:
        goal: 使用者目標
        iv: 當前 IV
        asset_type: 資產類型（股票/選擇權/期貨）

    Returns:
        推薦策略列表
    """
    strategies = []

    if asset_type == "股票":
        if goal == "鎖定當前利潤":
            if iv > 30:
                strategies.append("Collar（領口）- 高 IV 環境下用賣 Call 支付買 Put 成本")
            else:
                strategies.append("Protective Put（保護性賣權）- 直接買 Put 保護")

        elif goal == "產生現金流（收權利金）":
            if iv > 30:
                strategies.append("Covered Call（備兌看漲）- 高 IV 時權利金較高")
            else:
                strategies.append("Cash Secured Put（現金擔保賣權）- IV 較低時考慮賣 Put")

        elif goal == "降低持倉成本":
            strategies.append("Covered Call（備兌看漲）- 持續賣 Call 降低成本")

        elif goal == "保護下檔風險":
            if iv > 35:
                strategies.append("Collar（領口）- 零成本或低成本保護")
                strategies.append("Put Spread（熊市價差）- 降低保護成本")
            else:
                strategies.append("Protective Put（保護性賣權）")

        elif goal == "增加上檔曝險":
            if iv < 25:
                strategies.append("Buy Call（買進看漲）- 低 IV 時買方較便宜")
            else:
                strategies.append("Bull Call Spread（牛市看漲價差）- 降低成本")

    elif asset_type == "選擇權":
        if goal == "獲利了結":
            strategies.append("直接平倉 - 賣出現有部位鎖定獲利")
            if iv > 30:
                strategies.append("部分平倉 + 賣出更遠的 OTM - 保留部分曝險同時收權利金")

        elif goal == "調整部位（Roll）":
            strategies.append("時間 Roll - 換到更遠到期日，延長時間價值")
            strategies.append("Strike Roll - 調整 Strike，改變風險曝險")

        elif goal == "加碼部位":
            if iv < 25:
                strategies.append("買入更多相同部位 - 低 IV 時加碼")
            else:
                strategies.append("Spread 加碼 - 使用價差降低成本")

        elif goal == "對沖風險":
            strategies.append("反向部位對沖 - 買入相反方向保護")
            strategies.append("轉換為 Spread - 賣出另一腳限制風險")

        elif goal == "策略轉換":
            strategies.append("Straddle -> Strangle - 降低成本但擴大損益平衡區間")
            strategies.append("Naked -> Spread - 限制最大損失")

    else:  # 期貨
        if goal == "平倉出場":
            strategies.append("市價平倉 - 快速退出部位")
            strategies.append("限價平倉 - 等待更好價格")

        elif goal == "換月（Roll Over）":
            strategies.append("Calendar Roll - 平倉近月，建立遠月部位")
            strategies.append("價差 Roll - 同時操作兩個月份，鎖定價差")

        elif goal == "加碼部位":
            strategies.append("順勢加碼 - 趨勢明確時增加部位")
            strategies.append("金字塔加碼 - 分批建立部位降低風險")

        elif goal == "對沖風險":
            strategies.append("反向對沖 - 建立相反方向部位")
            strategies.append("選擇權保護 - 買入 Put/Call 保護期貨部位")

        elif goal == "價差交易（Spread）":
            strategies.append("Calendar Spread - 不同到期月份價差")
            strategies.append("Inter-Commodity Spread - 不同商品間價差")

    return strategies if strategies else ["無明確推薦，請諮詢專業顧問"]

# 生成策略建議
st.markdown("---")
st.subheader("🤖 Python 策略引擎")

recommended_strategies = recommend_strategies(goal, iv_30, asset_type)

st.info(f"**{asset_type}策略推薦：**")
for strategy in recommended_strategies:
    st.write(f"- {strategy}")

# AI 深度分析
st.markdown("---")
st.subheader("🧠 AI 策略師深度分析")

if st.button("🚀 取得 AI 策略建議", type="primary"):
    if ai_coach is None:
        st.error("AI 功能未啟用，請設定 GEMINI_API_KEY")
    else:
        with st.spinner("AI 正在分析情境..."):
            try:
                position_data = {
                    'asset_type': asset_type,
                    'symbol': symbol,
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'multiplier': multiplier,
                    'notional_value': notional_value
                }

                market_data = {
                    'current_price': current_price,
                    'iv_30': iv_30
                }

                scenario = {
                    'goal': goal,
                    'upcoming_events': upcoming_events
                }

                # 加入衍生品專屬資訊
                if asset_type == "選擇權":
                    position_data['strike'] = parsed_symbol.get('strike')
                    position_data['expiry'] = parsed_symbol.get('expiry')
                    position_data['option_type'] = parsed_symbol.get('option_type')
                elif asset_type == "期貨":
                    position_data['expiry'] = parsed_symbol.get('expiry')
                    position_data['underlying'] = parsed_symbol.get('underlying')

                ai_advice = ai_coach.generate_strategy_advice(
                    position_data=position_data,
                    market_data=market_data,
                    scenario=scenario,
                    recommended_strategies=recommended_strategies
                )

                st.success("✅ AI 分析完成")
                st.markdown(ai_advice)

            except Exception as e:
                st.error(f"AI 分析失敗：{str(e)}")

# 補充資訊
with st.expander("💡 關於選擇權策略"):
    st.markdown("""
    ### 常見策略說明

    **Collar（領口）**
    - 同時買 Put（保護）+ 賣 Call（收權利金）
    - 適合：高 IV 環境，想保護利潤但不想付太多成本
    - 缺點：限制了上檔收益

    **Covered Call（備兌看漲）**
    - 持有股票 + 賣出 Call
    - 適合：中性偏多，願意犧牲部分上檔換取收入
    - 缺點：如果股價大漲會被 Call 走

    **Protective Put（保護性賣權）**
    - 持有股票 + 買入 Put
    - 適合：看多但想買保險
    - 缺點：需付出權利金成本

    **IV 的影響**
    - **高 IV（>30%）**：權利金較貴，適合「賣方」策略
    - **低 IV（<20%）**：權利金較便宜，適合「買方」策略
    """)
