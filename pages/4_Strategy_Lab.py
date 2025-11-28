"""
策略實驗室頁面 (Strategy Lab)

功能：
1. 載入 AI_Trading_Journal 回測結果
2. 視覺化參數高原（Parameter Plateau）
3. AI 分析過擬合風險
4. 與實際交易績效對比
5. 生成策略報告
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from pathlib import Path
import sys

# 確保可以載入專案模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import TradingDatabase
from utils.backtest_loader import BacktestLoader
from utils.ai_strategy_advisor import AIStrategyAdvisor
from utils.derivatives_support import InstrumentParser

# 頁面配置
st.set_page_config(
    page_title="策略實驗室",
    page_icon="🔬",
    layout="wide"
)

# 初始化
@st.cache_resource
def init_components():
    """初始化資料庫、載入器和 AI 顧問"""
    db = TradingDatabase()
    loader = BacktestLoader()
    try:
        ai_advisor = AIStrategyAdvisor()
    except ValueError:
        ai_advisor = None
    return db, loader, ai_advisor

db, loader, ai_advisor = init_components()

# 頁面標題
st.title("🔬 策略實驗室")
st.markdown("載入並分析 AI_Trading_Journal 回測結果，識別穩健策略")
st.markdown("---")

# 警告：未設定 API Key
if ai_advisor is None:
    st.warning("⚠️ 未偵測到 GEMINI_API_KEY，AI 分析功能將無法使用。")

# 側邊欄：選擇回測結果
with st.sidebar:
    st.header("📂 載入回測結果")

    # 列出可用的回測檔案
    available_backtests = loader.list_available_backtests()

    if not available_backtests:
        st.warning("⚠️ 尚無回測結果")
        st.info("""
        **選項 A：在此頁面執行回測**
        點擊下方「🚀 執行新回測」按鈕

        **選項 B：使用命令列**
        ```bash
        uv run run_backtest.py --config your_config.json
        ```
        """)

        # 顯示「執行新回測」按鈕
        if st.button("🚀 執行新回測", type="primary"):
            st.info("💡 回測功能開發中，目前請使用選項 B 透過命令列執行")
            st.code("uv run run_backtest.py --config backtest_config.json", language="bash")

        st.stop()

    # 選擇回測檔案
    backtest_options = [
        f"{b['filename']} ({b['num_strategies']} 策略, {datetime.fromtimestamp(b['modified']).strftime('%Y-%m-%d %H:%M')})"
        for b in available_backtests
    ]

    selected_idx = st.selectbox(
        "選擇回測結果",
        range(len(backtest_options)),
        format_func=lambda i: backtest_options[i]
    )

    selected_backtest = available_backtests[selected_idx]

    # 顯示檔案資訊
    st.metric("檔案大小", f"{selected_backtest['size'] / 1024:.2f} KB")
    st.metric("策略數", selected_backtest['num_strategies'])

    # 載入按鈕
    load_button = st.button("📊 載入並分析", type="primary")

# 主要內容區
if load_button or 'backtest_df' in st.session_state:

    if load_button:
        # 載入回測結果
        with st.spinner("載入回測結果中..."):
            try:
                backtest_df = loader.load_backtest_result(selected_backtest['path'])
                st.session_state.backtest_df = backtest_df
                st.session_state.backtest_summary = loader.summarize_backtest(backtest_df)
                st.success(f"✅ 成功載入 {len(backtest_df)} 個策略組合")
            except Exception as e:
                st.error(f"❌ 載入失敗：{str(e)}")
                st.stop()

    backtest_df = st.session_state.backtest_df
    summary = st.session_state.backtest_summary

    # 檢測標的類型（如果 backtest_df 有 symbol 欄位）
    if 'symbol' in backtest_df.columns:
        # 解析所有標的
        symbol_sample = backtest_df['symbol'].iloc[0] if len(backtest_df) > 0 else "UNKNOWN"
        parsed = InstrumentParser.parse_symbol(symbol_sample)

        if parsed['instrument_type'] != 'stock':
            st.warning(f"""
            ⚠️ **衍生品回測警告**

            偵測到回測標的為 **{parsed['instrument_type'].upper()}**。

            **注意事項：**
            - 選擇權/期貨回測可能無法完全反映實際交易成本（手續費、滑價）
            - 選擇權的時間價值衰減（Theta）可能未被準確模擬
            - 建議將回測結果作為參考，而非絕對依據
            - 實際交易請搭配 AI 策略建議（頁面 5）
            """)

    # 顯示摘要統計
    st.subheader("📊 回測摘要統計")

    col1, col2, col3, col4 = st.columns(4)

    best_strategy = summary.get('best_strategy', {})
    overfitting = summary.get('overfitting_analysis', {})

    with col1:
        st.metric(
            "總策略數",
            summary['total_strategies']
        )

    with col2:
        if best_strategy:
            st.metric(
                "最佳 Sharpe",
                f"{best_strategy.get('metric_value', 0):.2f}"
            )

    with col3:
        st.metric(
            "穩定參數組合",
            len(overfitting.get('stable_params', []))
        )

    with col4:
        is_overfitted = overfitting.get('is_overfitted', False)
        st.metric(
            "過擬合風險",
            "高" if is_overfitted else "低",
            delta=None,
            delta_color="inverse" if is_overfitted else "normal"
        )

    # 顯示績效指標分布
    st.markdown("---")
    st.subheader("📈 績效指標分布")

    # 選擇要視覺化的指標
    numeric_cols = backtest_df.select_dtypes(include=['float64', 'int64']).columns.tolist()

    if numeric_cols:
        col1, col2 = st.columns(2)

        with col1:
            metric1 = st.selectbox("選擇指標 1", numeric_cols, index=0)

        with col2:
            metric2 = st.selectbox("選擇指標 2", numeric_cols, index=min(1, len(numeric_cols)-1))

        # 繪製散點圖
        fig = px.scatter(
            backtest_df,
            x=metric1,
            y=metric2,
            title=f"{metric1} vs {metric2}",
            hover_data=backtest_df.columns,
            color=metric2,
            color_continuous_scale='RdYlGn'
        )

        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        # 繪製直方圖
        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.histogram(
                backtest_df,
                x=metric1,
                title=f"{metric1} 分布",
                nbins=30
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.histogram(
                backtest_df,
                x=metric2,
                title=f"{metric2} 分布",
                nbins=30
            )
            st.plotly_chart(fig2, use_container_width=True)

    # 參數高原視覺化
    st.markdown("---")
    st.subheader("🗻 參數高原分析")

    stable_count = len(overfitting.get('stable_params', []))
    unstable_count = len(overfitting.get('unstable_params', []))

    if stable_count + unstable_count > 0:
        # 餅圖：穩定 vs 不穩定
        fig = go.Figure(data=[go.Pie(
            labels=['穩定參數區域', '不穩定參數區域'],
            values=[stable_count, unstable_count],
            marker=dict(colors=['#2ecc71', '#e74c3c'])
        )])

        fig.update_layout(
            title="參數穩健性分布",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # 顯示穩定參數組合
        with st.expander("🎯 查看穩定參數組合（高原區域）"):
            if overfitting.get('stable_params'):
                stable_df = pd.DataFrame(overfitting['stable_params'])
                st.dataframe(stable_df, use_container_width=True)
            else:
                st.info("無穩定參數組合")

    # AI 分析區
    if ai_advisor:
        st.markdown("---")
        st.subheader("🤖 AI 策略分析")

        tab1, tab2, tab3 = st.tabs(["參數穩健性", "策略報告", "實戰建議"])

        with tab1:
            if st.button("🔍 分析參數穩健性", key="analyze_robustness"):
                with st.spinner("AI 分析中..."):
                    try:
                        analysis = ai_advisor.analyze_parameter_robustness(summary)
                        st.markdown(analysis)
                    except Exception as e:
                        st.error(f"分析失敗：{str(e)}")

        with tab2:
            if st.button("📝 生成策略報告", key="generate_report"):
                with st.spinner("生成報告中..."):
                    try:
                        # 提取最佳策略的指標
                        best_metrics = {}
                        if best_strategy and 'strategy' in best_strategy:
                            best_metrics = best_strategy['strategy']

                        report = ai_advisor.generate_strategy_report(
                            strategy_name="AI_Trading_Journal 回測策略",
                            backtest_metrics=best_metrics
                        )
                        st.markdown(report)

                        # 儲存報告選項
                        if st.button("💾 儲存報告到資料庫"):
                            # 儲存到資料庫
                            backtest_id = db.add_backtest_result({
                                'strategy_name': 'AI_Trading_Journal',
                                'symbol': 'Multiple',
                                'start_date': datetime.now().strftime('%Y-%m-%d'),
                                'end_date': datetime.now().strftime('%Y-%m-%d'),
                                'parameters': best_metrics,
                                **best_metrics
                            })
                            st.success(f"✅ 報告已儲存 (ID: {backtest_id})")

                    except Exception as e:
                        st.error(f"報告生成失敗：{str(e)}")

        with tab3:
            st.markdown("### 市場環境選擇")
            market_regime = st.selectbox(
                "當前市場環境",
                ["bull", "bear", "neutral", "volatile"],
                format_func=lambda x: {
                    "bull": "🐂 牛市（上漲趨勢）",
                    "bear": "🐻 熊市（下跌趨勢）",
                    "neutral": "😐 中性（盤整）",
                    "volatile": "📈📉 高波動"
                }[x]
            )

            if st.button("💡 取得參數調整建議", key="get_suggestions"):
                with st.spinner("AI 分析中..."):
                    try:
                        current_params = {}
                        if best_strategy and 'strategy' in best_strategy:
                            current_params = best_strategy['strategy']

                        suggestions = ai_advisor.suggest_parameter_adjustment(
                            current_params=current_params,
                            market_regime=market_regime
                        )
                        st.markdown(suggestions)
                    except Exception as e:
                        st.error(f"建議生成失敗：{str(e)}")

    # 顯示原始數據
    st.markdown("---")
    st.subheader("📋 原始回測數據")

    with st.expander("查看完整數據表"):
        st.dataframe(backtest_df, use_container_width=True)

        # 匯出選項
        csv = backtest_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下載 CSV",
            data=csv,
            file_name=f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    # 尚未載入數據時的提示
    st.info("👈 請在左側選擇回測結果並點擊「載入並分析」")

    st.markdown("""
    ### 📖 使用說明

    #### 1. 執行回測
    **選項 A：UI 執行（未來功能）**
    - 直接在此頁面配置並執行回測
    - 即時查看進度與結果

    **選項 B：命令列執行（當前）**
    ```bash
    uv run run_backtest.py --config your_config.json
    ```

    #### 2. 回測結果位置
    回測結果將儲存在：
    - `records/metricstracker/*.parquet`

    #### 3. 載入分析
    返回本頁面，選擇回測檔案並載入

    #### 4. AI 分析
    - 參數穩健性分析
    - 過擬合風險評估
    - 實戰建議與報告生成

    ### 🎯 主要功能

    - **參數高原視覺化**：識別穩健參數組合
    - **績效指標分布**：多維度分析策略表現
    - **AI 策略顧問**：專業分析與建議
    - **與實際交易對比**：驗證策略有效性
    """)

# 側邊欄：已儲存的回測記錄
with st.sidebar:
    st.markdown("---")
    st.header("💾 已儲存的回測")

    saved_backtests = db.get_backtest_results()

    if saved_backtests:
        st.metric("總記錄數", len(saved_backtests))

        with st.expander("查看記錄"):
            for bt in saved_backtests[:5]:  # 只顯示最近 5 筆
                st.text(f"{bt['strategy_name']} - {bt['symbol']}")
                st.caption(f"Sharpe: {bt.get('sharpe_ratio', 'N/A')}")
    else:
        st.info("尚無儲存的回測記錄")
