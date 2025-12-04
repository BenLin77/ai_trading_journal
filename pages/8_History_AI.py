"""
AI 歷史交易分析頁面
讓 AI 分析過去一年的交易記錄，提供改善建議
"""

import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 頁面配置
st.set_page_config(
    page_title="AI 歷史分析 | AI Trading Journal",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS
from utils.ui_components import inject_custom_css
inject_custom_css()

st.title("🔍 AI 歷史交易分析")
st.markdown("讓 AI 分析你過去一年的交易記錄，找出可改善的地方")

# 檢查必要的環境變數
IBKR_TOKEN = os.getenv('IBKR_FLEX_TOKEN', '')
HISTORY_QUERY_ID = os.getenv('IBKR_HISTORY_QUERY_ID', '1344117')  # 預設使用你的 Query ID

if not IBKR_TOKEN:
    st.error("❌ 請先在 `.env` 設定 `IBKR_FLEX_TOKEN`")
    st.stop()

# --- 篩選區 ---
st.markdown("### 📅 選擇分析區間")

col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    # 預設區間選項
    period_options = {
        "過去一週": 7,
        "過去一個月": 30,
        "過去三個月": 90,
        "過去六個月": 180,
        "過去一年": 365,
        "自訂區間": 0,
    }
    selected_period = st.selectbox("快速選擇", list(period_options.keys()), index=2)

with col2:
    if selected_period == "自訂區間":
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=90))
    else:
        days = period_options[selected_period]
        start_date = datetime.now() - timedelta(days=days)
        st.date_input("開始日期", start_date, disabled=True)

with col3:
    end_date = st.date_input("結束日期", datetime.now())

# 標的篩選
col4, col5 = st.columns([3, 3])
with col4:
    symbol_filter = st.text_input("篩選特定標的（留空=全部）", placeholder="例如: ONDS, SMR, NVDA")
with col5:
    st.markdown("")
    st.markdown("")
    analyze_btn = st.button("🚀 開始 AI 分析", type="primary", use_container_width=True)

st.markdown("---")

# --- 分析結果區 ---
if analyze_btn:
    try:
        from utils.ibkr_flex_query import IBKRFlexQuery
        
        with st.spinner("正在從 IBKR 取得歷史交易資料（約 15-20 秒）..."):
            flex = IBKRFlexQuery()
            
            # 取得交易摘要
            summary = flex.get_trade_summary_for_ai(
                query_id=HISTORY_QUERY_ID,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                symbol=symbol_filter.strip().upper() if symbol_filter.strip() else None
            )
        
        if 'error' in summary and summary.get('trades', []) == []:
            st.warning(f"⚠️ {summary['error']}")
            st.stop()
        
        # 顯示統計數據
        st.markdown("### 📊 交易統計")
        stats = summary.get('statistics', {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("總交易筆數", f"{stats.get('total_trades', 0):,}")
        with col2:
            pnl = stats.get('total_realized_pnl', 0)
            st.metric("總已實現損益", f"${pnl:,.2f}", delta=f"{pnl:+,.2f}")
        with col3:
            st.metric("勝率", f"{stats.get('win_rate', 0):.1f}%")
        with col4:
            st.metric("總手續費", f"${abs(stats.get('total_commission', 0)):,.2f}")
        
        col5, col6 = st.columns(2)
        with col5:
            st.metric("平均獲利", f"${stats.get('avg_win', 0):,.2f}")
        with col6:
            st.metric("平均虧損", f"${stats.get('avg_loss', 0):,.2f}")
        
        # 按標的統計
        st.markdown("### 📈 按標的分類")
        symbol_stats = summary.get('by_symbol', {})
        if symbol_stats:
            import pandas as pd
            symbol_df = pd.DataFrame([
                {'標的': sym, '交易次數': data['trades'], '損益': data['pnl']}
                for sym, data in symbol_stats.items()
            ])
            symbol_df = symbol_df.sort_values('損益', ascending=False)
            
            # 用顏色標示損益
            st.dataframe(
                symbol_df.style.applymap(
                    lambda x: 'color: #00ff88' if isinstance(x, (int, float)) and x > 0 
                              else 'color: #ff6b6b' if isinstance(x, (int, float)) and x < 0 
                              else '',
                    subset=['損益']
                ),
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # --- AI 分析區 ---
        st.markdown("### 🤖 AI 深度分析")
        
        # 準備 AI Prompt
        ai_prompt = f"""
你是一位專業的量化交易顧問。請根據以下交易數據進行深度分析，並給出具體可執行的改善建議。

## 交易期間
{summary['period']['start']} 至 {summary['period']['end']}

## 統計摘要
- 總交易筆數: {stats.get('total_trades', 0)}
- 總已實現損益: ${stats.get('total_realized_pnl', 0):,.2f}
- 勝率: {stats.get('win_rate', 0):.1f}%
- 平均獲利: ${stats.get('avg_win', 0):,.2f}
- 平均虧損: ${stats.get('avg_loss', 0):,.2f}
- 總手續費: ${abs(stats.get('total_commission', 0)):,.2f}

## 按標的損益排名
{chr(10).join([f"- {sym}: {data['trades']} 筆, ${data['pnl']:+,.2f}" for sym, data in sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)[:10]])}

## 交易明細（最近 50 筆）
{summary['trades'][:50]}

---

請提供以下分析：

### 1. 整體表現評估
- 評估盈虧比是否健康
- 勝率與期望值分析

### 2. 交易習慣分析
- 是否有過度交易的傾向？
- 持倉時間是否合理？
- 是否有追高殺低的行為？

### 3. 最大虧損分析
- 指出虧損最嚴重的交易
- 分析可能的原因

### 4. 最成功交易分析
- 指出獲利最多的交易
- 可以複製的策略是什麼？

### 5. 具體改善建議
- 給出 3-5 個可立即執行的改善行動
- 每個建議都要具體、可量化

請用繁體中文回答，語氣專業但易懂。
"""
        
        # 檢查是否有 OpenAI API Key
        openai_key = os.getenv('OPENAI_API_KEY', '')
        google_key = os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        
        if openai_key or google_key:
            with st.spinner("AI 正在分析你的交易歷史..."):
                try:
                    if google_key:
                        # 使用 Gemini
                        import google.generativeai as genai
                        genai.configure(api_key=google_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(ai_prompt)
                        ai_response = response.text
                    else:
                        # 使用 OpenAI
                        from openai import OpenAI
                        client = OpenAI(api_key=openai_key)
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": ai_prompt}],
                            temperature=0.7,
                        )
                        ai_response = response.choices[0].message.content
                    
                    st.markdown(ai_response)
                    
                except Exception as e:
                    st.error(f"AI 分析失敗: {str(e)}")
                    st.markdown("#### 統計數據供參考：")
                    st.json(summary['statistics'])
        else:
            st.warning("⚠️ 未設定 AI API Key。請在 `.env` 設定 `GOOGLE_API_KEY` 或 `OPENAI_API_KEY`")
            st.markdown("#### 統計數據供參考：")
            st.json(summary['statistics'])
            
            # 顯示 prompt 供手動使用
            with st.expander("📋 複製 Prompt 到 ChatGPT / Claude"):
                st.code(ai_prompt, language="markdown")
        
    except Exception as e:
        st.error(f"❌ 發生錯誤: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# --- 說明區 ---
with st.expander("📖 使用說明"):
    st.markdown("""
    ### 如何使用
    
    1. **設定 IBKR Flex Query**：
       - 登入 IBKR 帳戶管理
       - 到 Flex Queries → 建立新查詢
       - 設定查詢期間為「過去一年」
       - 格式選擇 CSV
       - 記下 Query ID
    
    2. **設定環境變數**（在 `.env` 檔案）：
       ```
       IBKR_FLEX_TOKEN=your_token_here
       IBKR_HISTORY_QUERY_ID=1344117
       GOOGLE_API_KEY=your_gemini_key  # 或 OPENAI_API_KEY
       ```
    
    3. **選擇分析區間**並點擊「開始 AI 分析」
    
    ### 分析內容
    - 整體表現評估（盈虧比、勝率）
    - 交易習慣分析（是否過度交易）
    - 最大虧損 / 最成功交易分析
    - 具體可執行的改善建議
    """)
