"""
績效成績單頁面 (Report Card Module)

功能：
1. 顯示全局 KPI
2. 按標的分析盈虧
3. 按時段分析盈虧
4. AI 績效評語與改進建議
"""

import streamlit as st
import pandas as pd
from database import TradingDatabase
from utils.charts import (
    create_pnl_by_symbol_chart,
    create_pnl_by_hour_chart,
    create_win_loss_distribution
)
from utils.ai_coach import AICoach
from utils.derivatives_support import DerivativesAnalyzer

# 頁面配置
st.set_page_config(
    page_title="績效成績單",
    page_icon="📊",
    layout="wide"
)

# 初始化
@st.cache_resource
def init_components():
    """初始化資料庫和 AI"""
    db = TradingDatabase()
    try:
        ai_coach = AICoach()
    except ValueError:
        ai_coach = None
    return db, ai_coach

db, ai_coach = init_components()

# 頁面標題
st.title("📊 我的交易成績單")
st.markdown("長期績效追蹤與 AI 改進建議")
st.markdown("---")

# 載入全局統計數據
stats = db.get_trade_statistics()

if stats['total_trades'] == 0:
    st.warning("⚠️ 資料庫中沒有交易紀錄，請先在主頁面上傳 CSV 檔案")
    st.stop()

# 顯示關鍵 KPI
st.subheader("🎯 關鍵績效指標")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "總盈虧",
        f"${stats['total_pnl']:,.2f}",
        delta=None,
        delta_color="normal"
    )

with col2:
    st.metric(
        "勝率",
        f"{stats['win_rate']:.1f}%",
        delta=None,
        delta_color="normal"
    )

with col3:
    st.metric(
        "平均獲利",
        f"${stats['avg_win']:,.2f}",
        delta=None,
        delta_color="normal"
    )

with col4:
    st.metric(
        "平均虧損",
        f"${stats['avg_loss']:,.2f}",
        delta=None,
        delta_color="inverse"
    )

with col5:
    st.metric(
        "獲利因子",
        f"{stats['profit_factor']:.2f}",
        delta=None,
        delta_color="normal"
    )

# 次要指標
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("總交易次數", stats['total_trades'])

with col2:
    st.metric("獲利交易", stats['wins'], delta_color="normal")

with col3:
    st.metric("虧損交易", stats['losses'], delta_color="inverse")

# 績效警示
st.markdown("---")

# 檢查常見問題
warnings = []

if stats['avg_loss'] > stats['avg_win'] * 1.5:
    warnings.append("⚠️ **風險警告**：平均虧損顯著大於平均獲利，建議改善停損紀律")

if stats['win_rate'] < 40:
    warnings.append("⚠️ **勝率過低**：勝率低於 40%，可能需要重新評估進場策略")

if stats['profit_factor'] < 1.0:
    warnings.append("🚨 **獲利因子小於 1**：總虧損大於總獲利，需立即改進交易系統")

if warnings:
    st.subheader("🚨 績效警示")
    for warning in warnings:
        st.warning(warning)

# 衍生品分析
st.markdown("---")
st.subheader("📐 衍生品交易分析")

all_trades = db.get_trades()
if all_trades:
    trades_df = pd.DataFrame(all_trades)
    derivatives_analyzer = DerivativesAnalyzer()

    # 豐富化數據
    enriched = derivatives_analyzer.enrich_trades(trades_df)

    # 按交易類型分類
    instrument_counts = enriched['instrument_type'].value_counts()
    instrument_pnl = enriched.groupby('instrument_type')['realized_pnl'].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        stock_count = instrument_counts.get('stock', 0)
        stock_pnl = instrument_pnl.get('stock', 0)
        st.metric(
            "📈 股票交易",
            f"{stock_count} 筆",
            delta=f"${stock_pnl:,.2f}" if stock_count > 0 else None,
            delta_color="normal"
        )

    with col2:
        option_count = instrument_counts.get('option', 0)
        option_pnl = instrument_pnl.get('option', 0)
        st.metric(
            "📊 選擇權交易",
            f"{option_count} 筆",
            delta=f"${option_pnl:,.2f}" if option_count > 0 else None,
            delta_color="normal"
        )

    with col3:
        futures_count = instrument_counts.get('futures', 0)
        futures_pnl = instrument_pnl.get('futures', 0)
        st.metric(
            "📉 期貨交易",
            f"{futures_count} 筆",
            delta=f"${futures_pnl:,.2f}" if futures_count > 0 else None,
            delta_color="normal"
        )

    # 選擇權詳細分析
    options_metrics = derivatives_analyzer.calculate_options_metrics(trades_df)
    if options_metrics.get('has_options'):
        st.markdown("#### 🎯 選擇權績效詳情")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總交易筆數", options_metrics['total_options_trades'])

        with col2:
            st.metric("Call 交易", options_metrics['call_trades'])

        with col3:
            st.metric("Put 交易", options_metrics['put_trades'])

        with col4:
            st.metric("總權利金", f"${options_metrics['total_premium']:,.2f}")

        # 策略識別
        strategies = options_metrics['strategies']
        if strategies['total_strategies'] > 0:
            st.markdown("**識別的選擇權策略組合：**")

            strategy_summary = {}
            for strat in strategies['strategies']:
                strategy_name = strat['strategy']
                strategy_summary[strategy_name] = strategy_summary.get(strategy_name, 0) + 1

            strategy_df = pd.DataFrame([
                {'策略類型': k, '次數': v}
                for k, v in strategy_summary.items()
            ])
            st.dataframe(strategy_df, use_container_width=True, hide_index=True)

    # 期貨詳細分析
    futures_metrics = derivatives_analyzer.calculate_futures_metrics(trades_df)
    if futures_metrics.get('has_futures'):
        st.markdown("#### 📊 期貨績效詳情")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("總交易筆數", futures_metrics['total_futures_trades'])

        with col2:
            st.metric("總合約數", int(futures_metrics['total_contracts']))

        with col3:
            st.metric("名義價值", f"${futures_metrics['total_notional']:,.2f}")

        # 期貨標的分布
        futures_only = enriched[enriched['instrument_type'] == 'futures']
        if not futures_only.empty:
            underlying_counts = futures_only['underlying'].value_counts()
            st.markdown("**交易標的分布：**")
            underlying_df = pd.DataFrame([
                {'標的': k, '交易次數': v}
                for k, v in underlying_counts.items()
            ])
            st.dataframe(underlying_df, use_container_width=True, hide_index=True)
else:
    st.info("無交易紀錄，無法分析衍生品交易")

# 視覺化圖表
st.markdown("---")
st.subheader("📈 視覺化分析")

tab1, tab2, tab3 = st.tabs(["按標的分析", "按時段分析", "勝負分布"])

with tab1:
    st.markdown("### 各標的盈虧")
    pnl_by_symbol = db.get_pnl_by_symbol()

    if pnl_by_symbol:
        fig_symbol = create_pnl_by_symbol_chart(pnl_by_symbol)
        st.plotly_chart(fig_symbol, use_container_width=True)

        # 找出最好和最差標的
        best_symbol = max(pnl_by_symbol.items(), key=lambda x: x[1])
        worst_symbol = min(pnl_by_symbol.items(), key=lambda x: x[1])

        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ **最佳標的**：{best_symbol[0]} (${best_symbol[1]:,.2f})")
        with col2:
            st.error(f"❌ **最差標的**：{worst_symbol[0]} (${worst_symbol[1]:,.2f})")
    else:
        st.info("無數據")

with tab2:
    st.markdown("### 時段盈虧（找出魔鬼時刻）")
    pnl_by_hour = db.get_pnl_by_hour()

    if pnl_by_hour:
        fig_hour = create_pnl_by_hour_chart(pnl_by_hour)
        st.plotly_chart(fig_hour, use_container_width=True)

        # 找出最差時段
        worst_hours = sorted(pnl_by_hour.items(), key=lambda x: x[1])[:3]

        st.warning("⚠️ **最差時段（魔鬼時刻）**：")
        for hour, pnl in worst_hours:
            st.write(f"- {hour:02d}:00 - {hour+1:02d}:00：${pnl:,.2f}")
    else:
        st.info("無數據")

with tab3:
    st.markdown("### 交易勝負分布")

    fig_dist = create_win_loss_distribution(stats)
    st.plotly_chart(fig_dist, use_container_width=True)

    # 計算賺賠比
    if stats['avg_loss'] > 0:
        risk_reward_ratio = stats['avg_win'] / stats['avg_loss']
        st.info(f"📊 **賺賠比**：{risk_reward_ratio:.2f}（平均獲利 / 平均虧損）")

        if risk_reward_ratio < 1.5:
            st.warning("建議：賺賠比偏低，應該讓獲利跑得更遠，或更早停損")

# AI 績效評語
st.markdown("---")
st.subheader("🧠 AI 績效教練評語")

if ai_coach is None:
    st.info("AI 功能需要設定 GEMINI_API_KEY")
else:
    if st.button("🚀 取得 AI 績效評語", type="primary"):
        with st.spinner("AI 正在分析你的績效..."):
            try:
                # 組合洞察
                insights = []

                # 最差標的
                if pnl_by_symbol:
                    worst_symbol = min(pnl_by_symbol.items(), key=lambda x: x[1])
                    insights.append(f"最弱標的：{worst_symbol[0]}（虧損 ${abs(worst_symbol[1]):,.2f}）")

                # 最差時段
                if pnl_by_hour:
                    worst_hour = min(pnl_by_hour.items(), key=lambda x: x[1])
                    insights.append(f"魔鬼時刻：{worst_hour[0]:02d}:00-{worst_hour[0]+1:02d}:00（虧損 ${abs(worst_hour[1]):,.2f}）")

                # 賺賠比問題
                if stats['avg_loss'] > 0:
                    risk_reward_ratio = stats['avg_win'] / stats['avg_loss']
                    insights.append(f"賺賠比：{risk_reward_ratio:.2f}（平均獲利 ${stats['avg_win']:.2f} vs 平均虧損 ${stats['avg_loss']:.2f}）")

                insights_text = "\n".join(insights) if insights else "無特別洞察"

                ai_review = ai_coach.generate_performance_review(
                    stats=stats,
                    insights=insights_text
                )

                st.success("✅ AI 分析完成")
                st.markdown(ai_review)

            except Exception as e:
                st.error(f"AI 分析失敗：{str(e)}")

# 詳細交易列表
st.markdown("---")
st.subheader("📋 詳細交易紀錄")

with st.expander("查看所有交易"):
    all_trades = db.get_trades()

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])

        # 格式化顯示
        display_df = trades_df[[
            'datetime', 'symbol', 'action', 'quantity', 'price', 'realized_pnl'
        ]].copy()

        display_df.columns = ['時間', '標的', '動作', '數量', '價格', '已實現盈虧']

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # 匯出功能 - 多格式支援
        from utils.export import DataExporter

        st.markdown("### 📥 匯出數據")

        col1, col2 = st.columns([3, 1])

        with col1:
            export_format = st.selectbox(
                "選擇匯出格式",
                ['CSV', 'Excel', 'JSON'],
                help="Excel 格式會包含額外的統計摘要工作表"
            )

        with col2:
            st.write("")  # 空白以對齊
            st.write("")

        try:
            exporter = DataExporter()
            data, filename, mime = exporter.export_trades(
                trades_df,
                format=export_format.lower()
            )

            st.download_button(
                label=f"📥 下載 {export_format} 檔案",
                data=data,
                file_name=filename,
                mime=mime,
                type="primary",
                use_container_width=True
            )

            if export_format == 'Excel':
                st.info("💡 Excel 檔案包含「交易紀錄」和「統計摘要」兩個工作表")

        except Exception as e:
            st.error(f"匯出失敗：{str(e)}")
    else:
        st.info("無交易紀錄")

# 日誌回顧
st.markdown("---")
st.subheader("📝 交易日誌回顧")

with st.expander("查看所有日誌"):
    journals = db.get_journal_entries()

    if journals:
        for journal in journals:
            st.markdown(f"**{journal['trade_date']} - {journal['symbol']}**")
            st.write(f"心情：{journal['mood']}")
            st.write(f"論點：{journal['thesis']}")
            st.write(f"教訓：{journal['key_takeaway']}")
            st.markdown("---")
    else:
        st.info("尚無日誌紀錄")
