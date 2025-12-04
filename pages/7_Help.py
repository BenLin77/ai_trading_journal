"""
系統說明 - AI 交易日誌

關於本系統的完整功能說明與使用指南
"""

import streamlit as st
from utils.styles import inject_custom_css, render_header_with_subtitle
from config.theme import COLORS

st.set_page_config(
    page_title="系統說明 | AI Trading Journal",
    page_icon="ℹ️",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

render_header_with_subtitle(
    title="ℹ️ 系統說明",
    subtitle="AI 交易日誌功能介紹與使用指南"
)

# 功能概覽
st.markdown("## 🎯 功能概覽")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📊 首頁儀表板
    - 累計盈虧曲線圖（Robinhood 風格）
    - 核心 KPI 指標：勝率、平均獲利/虧損、獲利因子
    - 持倉卡片與 AI 點位分析
    - IBKR Flex Query 自動同步
    
    ### 📈 交易檢討
    - 單一標的深度分析
    - 全部標的綜合檢討
    - K 線圖 + 交易標記
    - AI 教練對話
    """)

with col2:
    st.markdown("""
    ### 🎯 策略實驗室
    - AI 策略建議與優化
    - What-if 情境分析
    - 選擇權策略偵測
    
    ### 📊 績效報告卡
    - 長期績效追蹤
    - 標的盈虧分析
    - 時段盈虧分析（找出魔鬼時刻）
    - 勝負分布圖
    """)

st.markdown("---")

# 資料來源設定
st.markdown("## ⚙️ 資料來源設定")

st.markdown("""
### 支援的資料來源

| 來源 | 說明 | 設定方式 |
|------|------|----------|
| **IBKR Flex Query** | 自動同步交易與庫存 | 在 `.env` 設定 `IBKR_FLEX_TOKEN`、`IBKR_TRADES_QUERY_ID`、`IBKR_POSITIONS_QUERY_ID` |
| **CSV 上傳** | 手動上傳 CSV 報表 | 在首頁使用上傳功能 |
| **Google Sheet** | 雲端自動同步 | 在 `.env` 設定 `GOOGLE_SHEET_URL` |
| **本地 CSV** | 自動讀取本地檔案 | 在 `.env` 設定 `AUTO_IMPORT_CSV_PATH` |
""")

st.markdown("---")

# AI 功能設定
st.markdown("## 🤖 AI 功能設定")

st.markdown("""
本系統支援兩種 AI 模型：

### DeepSeek（優先）
- 在 `.env` 設定 `DEEPSEEK_API_KEY`
- 成本效益較高

### Google Gemini（備用）
- 在 `.env` 設定 `GEMINI_API_KEY`
- 當 DeepSeek 未設定時自動使用

**AI 功能包含：**
- 交易檢討教練對話
- 策略優化建議
- 持倉點位分析（加碼/減碼/停損建議）
- 投資組合風險評估
""")

st.markdown("---")

# CSV 格式說明
st.markdown("## 📄 CSV 格式說明")

st.markdown("""
### 必要欄位

| 欄位名稱 | 說明 | 範例 |
|----------|------|------|
| `Date` | 交易日期時間 | 2024-01-15 09:30:00 |
| `Symbol` | 標的代號 | AAPL |
| `Side` | 買賣方向 | BUY / SELL |
| `Quantity` | 數量 | 100 |
| `Price` | 成交價格 | 185.50 |

### 可選欄位

| 欄位名稱 | 說明 |
|----------|------|
| `Commission` | 手續費 |
| `Strike` | 選擇權 Strike Price |
| `Expiry` | 選擇權到期日 |
| `Right` | 選擇權類型 (C/P) |
""")

st.markdown("---")

# 側邊欄資訊
st.sidebar.markdown("---")
st.sidebar.info("""
**快速連結**
- 🏠 [首頁](/)
- 📈 [交易檢討](/Review)
- 🎯 [策略實驗室](/Strategy)
- 📊 [績效報告卡](/Report_Card)
""")
