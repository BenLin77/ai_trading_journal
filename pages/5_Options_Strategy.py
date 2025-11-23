"""
選擇權策略建議頁面

功能：
1. 輸入標的與市場看法
2. AI 建議適合的選擇權策略
3. 計算風險/報酬比
4. Greeks 說明與操作注意事項
"""

import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ai_coach import AICoach

# 頁面配置
st.set_page_config(
    page_title="選擇權策略建議",
    page_icon="💡",
    layout="wide"
)

# 初始化 AI
@st.cache_resource
def init_ai():
    try:
        return AICoach()
    except:
        return None

ai_coach = init_ai()

st.title("💡 選擇權策略 AI 顧問")
st.markdown("根據你的市場看法，AI 推薦最適合的選擇權策略")
st.markdown("---")

if ai_coach is None:
    st.error("⚠️ 需要設定 GEMINI_API_KEY")
    st.stop()

# 輸入區
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 標的資訊")

    symbol = st.text_input("標的代號", value="AAPL", help="輸入美股代號").upper()

    # 抓取即時資料
    if st.button("📈 載入即時數據", type="primary"):
        with st.spinner("載入中..."):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1mo")

                st.session_state.current_price = hist['Close'].iloc[-1]
                st.session_state.ticker_info = info

                st.success(f"✅ {symbol} 當前價格: ${st.session_state.current_price:.2f}")
            except:
                st.error("❌ 無法載入數據，請檢查代號")

    if 'current_price' in st.session_state:
        st.metric("即時股價", f"${st.session_state.current_price:.2f}")

        # 顯示基本資訊
        if 'ticker_info' in st.session_state:
            info = st.session_state.ticker_info
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("52週高", f"${info.get('fiftyTwoWeekHigh', 0):.2f}")
            with col_b:
                st.metric("52週低", f"${info.get('fiftyTwoWeekLow', 0):.2f}")

with col2:
    st.subheader("🎯 市場看法")

    market_view = st.selectbox(
        "方向預期",
        ["📈 看漲 (Bullish)", "📉 看跌 (Bearish)", "↔️ 中性 (Neutral)", "📊 高波動"],
        help="你對標的未來走勢的看法"
    )

    time_horizon = st.selectbox(
        "時間範圍",
        ["1-2 週", "3-4 週", "1-2 個月", "3 個月以上"],
        index=1
    )

    risk_tolerance = st.select_slider(
        "風險承受度",
        options=["保守", "中等", "積極", "非常積極"],
        value="中等"
    )

    capital = st.number_input(
        "可用資金 ($)",
        min_value=100,
        max_value=1000000,
        value=5000,
        step=100
    )

st.markdown("---")

# 生成策略建議
if st.button("🤖 AI 策略建議", type="primary", use_container_width=True):
    if 'current_price' not in st.session_state:
        st.warning("⚠️ 請先載入標的資料")
        st.stop()

    with st.spinner("AI 分析中..."):
        # 整理輸入資訊
        context = f"""
標的: {symbol}
當前價格: ${st.session_state.current_price:.2f}
市場看法: {market_view}
時間範圍: {time_horizon}
風險承受度: {risk_tolerance}
可用資金: ${capital:,.0f}
"""

        if 'ticker_info' in st.session_state:
            info = st.session_state.ticker_info
            context += f"""
52週高點: ${info.get('fiftyTwoWeekHigh', 0):.2f}
52週低點: ${info.get('fiftyTwoWeekLow', 0):.2f}
Beta: {info.get('beta', 'N/A')}
"""

        # 呼叫 AI
        prompt = f"""
你是一位資深選擇權交易顧問。請根據以下資訊，提供詳細的選擇權策略建議：

{context}

請提供：

## 1. 推薦策略（至少 3 個）

對於每個策略，包含：
- **策略名稱**（中英文）
- **適合原因**（為什麼適合這個市場看法）
- **建議履約價** (Strike Price)
- **建議到期日**（根據時間範圍）
- **預估成本/權利金**
- **最大獲利**
- **最大虧損**
- **損益平衡點**
- **優點與缺點**

## 2. Greeks 解釋

簡單說明 Delta、Gamma、Theta、Vega 對這些策略的影響。

## 3. 風險提醒

- 需要注意的關鍵風險
- 停損建議
- 何時應該調整或平倉

## 4. 實戰建議

- 進場時機
- 部位管理
- 避免的常見錯誤

請用繁體中文，語氣專業但易懂。針對 {risk_tolerance} 風險偏好的投資人。
"""

        try:
            response = ai_coach.model.generate_content(prompt)
            st.session_state.ai_response = response.text
        except Exception as e:
            st.error(f"AI 分析失敗：{str(e)}")
            st.stop()

# 顯示結果
if 'ai_response' in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.ai_response)

    # 儲存建議
    st.markdown("---")
    with st.expander("💾 儲存此建議"):
        notes = st.text_area("備註（可選）", placeholder="記錄你的想法或調整...")

        if st.button("儲存到交易日誌"):
            from database import TradingDatabase
            db = TradingDatabase()

            db.add_journal_entry(
                trade_date=datetime.now().strftime('%Y-%m-%d'),
                symbol=symbol,
                thesis=f"選擇權策略建議\\n{market_view}\\n{st.session_state.ai_response[:500]}",
                mood="📊 策略分析",
                key_takeaway=notes
            )

            st.success("✅ 已儲存到日誌")
            st.balloons()

# 側邊欄：快速參考
with st.sidebar:
    st.header("📚 策略快速參考")

    st.markdown("""
### 常見策略

**看漲策略**
- 🔵 Long Call - 最簡單，適合強烈看漲
- 🔵 Bull Call Spread - 降低成本，限制獲利
- 🔵 Cash-Secured Put - 收權利金，願意買進

**看跌策略**
- 🔴 Long Put - 保護或投機
- 🔴 Bear Put Spread - 降低成本
- 🔴 Covered Call - 持股收租

**中性策略**
- 🟡 Iron Condor - 賺時間價值
- 🟡 Butterfly - 低成本，大獲利（低機率）
- 🟡 Calendar Spread - 賺時間價值差

**高波動策略**
- 🟣 Straddle - 不確定方向，預期大波動
- 🟣 Strangle - 成本較低的 Straddle
""")

    st.markdown("---")

    st.markdown("""
### Greeks 簡易說明

- **Delta (Δ)**: 股價變動 $1，選擇權價格變動多少
- **Gamma (Γ)**: Delta 的變化率
- **Theta (Θ)**: 時間衰減，每日損失的權利金
- **Vega (ν)**: IV 變動 1%，選擇權價格變動多少
""")

    st.markdown("---")
    st.caption("💡 建議僅供參考，實際交易請自行評估風險")
