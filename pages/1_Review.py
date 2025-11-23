"""
交易檢討頁面 (Review Module)

功能：
1. 選擇標的和日期範圍
2. 顯示整合 K 線圖與交易標記
3. AI 教練對話介面
4. 儲存交易日誌
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from database import TradingDatabase
from utils.analysis import TradingAnalyzer
from utils.charts import create_trading_chart
from utils.ai_coach import AICoach
from utils.derivatives_support import InstrumentParser, DerivativesAnalyzer

# 頁面配置
st.set_page_config(
    page_title="交易檢討",
    page_icon="📈",
    layout="wide"
)

# 初始化
@st.cache_resource
def init_components():
    """初始化資料庫和分析器"""
    db = TradingDatabase()
    analyzer = TradingAnalyzer()
    try:
        ai_coach = AICoach()
    except ValueError:
        ai_coach = None
    return db, analyzer, ai_coach

db, analyzer, ai_coach = init_components()

# 頁面標題
st.title("📈 交易檢討")
st.markdown("與 AI 教練深度分析你的交易決策")
st.markdown("---")

# 警告：未設定 API Key
if ai_coach is None:
    st.warning("⚠️ 未偵測到 GEMINI_API_KEY，AI 對話功能將無法使用。請在 `.env` 檔案中設定。")

# 左側控制面板
with st.sidebar:
    st.header("🎯 選擇檢討範圍")

    # 取得所有標的
    symbols = db.get_all_symbols()

    if not symbols:
        st.error("❌ 資料庫中沒有交易紀錄，請先在主頁面上傳 CSV 檔案")
        st.stop()

    # 標的選擇
    selected_symbol = st.selectbox(
        "標的代號",
        symbols,
        help="選擇要檢討的標的（股票/選擇權/期貨）"
    )

    # 解析標的類型
    parsed_symbol = InstrumentParser.parse_symbol(selected_symbol)

    if parsed_symbol['instrument_type'] != 'stock':
        st.info(f"📊 {parsed_symbol['instrument_type'].upper()}: {parsed_symbol['underlying']}")
        if parsed_symbol['instrument_type'] == 'option':
            st.caption(f"Strike: ${parsed_symbol['strike']}, Expiry: {parsed_symbol['expiry']}, Type: {parsed_symbol['option_type']}")
        elif parsed_symbol['instrument_type'] == 'futures':
            st.caption(f"Expiry: {parsed_symbol['expiry']}, Multiplier: {parsed_symbol['multiplier']}")

    # 日期範圍
    date_range = st.date_input(
        "日期範圍",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        help="選擇要分析的時間區間"
    )

    if len(date_range) == 2:
        start_date = date_range[0].strftime('%Y-%m-%d')
        end_date = date_range[1].strftime('%Y-%m-%d')
    else:
        st.warning("請選擇完整的日期範圍")
        st.stop()

    # K 線週期
    interval = st.selectbox(
        "K 線週期",
        ['1m', '5m', '15m', '30m', '1h', '1d'],
        index=1,
        help="選擇 K 線的時間週期"
    )

    # 載入按鈕
    load_button = st.button("📊 載入數據", type="primary")

# 主要內容區
if load_button:
    # 建立進度追蹤
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # 步驟 1: 從資料庫載入交易紀錄
        status_text.text("📂 步驟 1/4：載入交易紀錄...")
        progress_bar.progress(0.25)

        trades = db.get_trades(
            symbol=selected_symbol,
            start_date=start_date,
            end_date=end_date
        )

        if not trades:
            progress_bar.empty()
            status_text.empty()
            st.error(f"在 {start_date} 到 {end_date} 期間沒有 {selected_symbol} 的交易紀錄")
            st.stop()

        trades_df = pd.DataFrame(trades)
        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])

        # 步驟 2: 從 yfinance 抓取 K 線數據
        # 如果是選擇權/期貨，使用 underlying symbol
        underlying_symbol = parsed_symbol['underlying']
        is_derivative = parsed_symbol['instrument_type'] != 'stock'

        status_text.text(f"📈 步驟 2/4：抓取 {underlying_symbol} K 線數據...")
        progress_bar.progress(0.50)

        ticker = yf.Ticker(underlying_symbol)

        # 調整日期範圍（擴展幾天以獲得更完整的數據）
        extended_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
        extended_end = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

        ohlc_df = ticker.history(
            start=extended_start,
            end=extended_end,
            interval=interval
        )

        if ohlc_df.empty:
            progress_bar.empty()
            status_text.empty()
            st.error(f"無法取得 {underlying_symbol} 的 K 線數據")
            st.info("""
            **可能原因：**
            - 標的代號錯誤（請使用美股代號，例如 AAPL）
            - 日期範圍無可用數據
            - yfinance API 暫時無法連接
            """)
            st.stop()

        # 重置索引並重命名欄位
        ohlc_df = ohlc_df.reset_index()
        ohlc_df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"載入數據時發生錯誤：{str(e)}")
        with st.expander("查看詳細錯誤"):
            st.code(str(e))
        st.stop()

    # 步驟 3: Python 規則引擎分析
    status_text.text("🔍 步驟 3/4：分析交易模式...")
    progress_bar.progress(0.75)

    issues = analyzer.analyze_trades_with_bars(trades_df, ohlc_df)

    # 步驟 4: 生成圖表
    status_text.text("📊 步驟 4/4：生成互動圖表...")
    progress_bar.progress(0.95)

    fig = create_trading_chart(ohlc_df, trades_df, selected_symbol)

    # 完成
    progress_bar.progress(1.0)
    status_text.text("✅ 載入完成！")

    import time
    time.sleep(0.5)

    # 清除進度指示
    progress_bar.empty()
    status_text.empty()

    # 顯示成功訊息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success(f"✅ 載入了 {len(trades_df)} 筆交易紀錄")
    with col2:
        st.success(f"✅ 載入了 {len(ohlc_df)} 根 K 棒")
    with col3:
        if is_derivative:
            st.info(f"📊 {parsed_symbol['instrument_type'].upper()}")
        else:
            st.info("📈 股票交易")

    # 顯示分析結果
    st.subheader("🔍 交易行為與心理分析")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "疑似 FOMO (追高)",
            issues['summary']['total_chasing'],
            delta=None,
            delta_color="inverse"
        )

    with col2:
        st.metric(
            "疑似恐慌 (殺低)",
            issues['summary']['total_panic_selling'],
            delta=None,
            delta_color="inverse"
        )

    with col3:
        st.metric(
            "高風險接刀",
            issues['summary']['total_poor_timing'],
            delta=None,
            delta_color="inverse"
        )

    with col4:
        st.metric(
            "總警示",
            issues['summary']['total_issues'],
            delta=None,
            delta_color="inverse"
        )

    if issues['summary']['total_issues'] > 0:
        with st.expander("⚠️ 查看詳細分析"):
            if issues['chasing_price']:
                st.write("**🔥 疑似 FOMO / 追高：**")
                for issue in issues['chasing_price']:
                    st.write(f"- {issue['message']}")

            if issues['panic_selling']:
                st.write("**❄️ 疑似恐慌 / 殺低：**")
                for issue in issues['panic_selling']:
                    st.write(f"- {issue['message']}")
            
            if issues['poor_timing']:
                st.write("**🔪 高風險操作：**")
                for issue in issues['poor_timing']:
                    st.write(f"- {issue['message']}")

    # 衍生品資訊摘要（如果適用）
    if is_derivative:
        st.markdown("---")
        st.subheader("📐 衍生品資訊")

        if parsed_symbol['instrument_type'] == 'option':
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("標的", parsed_symbol['underlying'])
            with col2:
                st.metric("Strike", f"${parsed_symbol['strike']}")
            with col3:
                st.metric("到期日", parsed_symbol['expiry'])
            with col4:
                st.metric("類型", parsed_symbol['option_type'])

            # 計算總權利金
            total_premium = (trades_df['price'] * trades_df['quantity'] * parsed_symbol['multiplier']).sum()
            st.info(f"💰 總權利金：${total_premium:,.2f}")

        elif parsed_symbol['instrument_type'] == 'futures':
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("標的", parsed_symbol['underlying'])
            with col2:
                st.metric("到期日", parsed_symbol['expiry'])
            with col3:
                st.metric("合約倍數", parsed_symbol['multiplier'])

            # 計算名義價值
            notional_value = (trades_df['price'] * trades_df['quantity'] * parsed_symbol['multiplier']).sum()
            st.info(f"💰 名義價值：${notional_value:,.2f}")

    # 4. 繪製圖表
    st.subheader("📊 交易檢討圖")
    if is_derivative:
        st.caption(f"圖表顯示 {underlying_symbol} 的 K 線（{parsed_symbol['instrument_type']} 的標的資產）")

    fig = create_trading_chart(ohlc_df, trades_df, underlying_symbol)
    st.plotly_chart(fig, use_container_width=True)

    # 5. AI 教練對話區
    st.markdown("---")
    st.subheader("💬 AI 教練對話")

    if ai_coach is None:
        st.info("AI 對話功能需要設定 GEMINI_API_KEY")
    else:
        # 生成會話 ID
        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"{selected_symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 初始化對話
        if 'chat_messages' not in st.session_state:
            st.session_state.chat_messages = []

            # AI 首次提問
            analysis_context = analyzer.generate_ai_prompt_context(issues)

            # 加入衍生品資訊到摘要
            if is_derivative:
                instrument_info = f"{parsed_symbol['instrument_type'].upper()}: {selected_symbol}"
                if parsed_symbol['instrument_type'] == 'option':
                    instrument_info += f" (Strike ${parsed_symbol['strike']}, {parsed_symbol['option_type']})"
                trade_summary = f"{len(trades_df)} 筆{parsed_symbol['instrument_type']}交易，總盈虧：${trades_df['realized_pnl'].sum():.2f}"
            else:
                instrument_info = f"股票: {selected_symbol}"
                trade_summary = f"{len(trades_df)} 筆交易，總盈虧：${trades_df['realized_pnl'].sum():.2f}"

            ohlc_summary = f"K 線數據：{len(ohlc_df)} 根，週期 {interval}"

            # 取得過去的記憶 (Long-term Memory)
            try:
                global_history = db.get_global_chat_history(limit=30)
                formatted_history = ""
                if global_history:
                    formatted_history = "--- 過去對話紀錄 ---\n"
                    for msg in global_history:
                        role = "User" if msg['role'] == 'user' else "AI Coach"
                        formatted_history += f"{role}: {msg['content']}\n"
                    formatted_history += "--- 紀錄結束 ---\n"
            except Exception:
                formatted_history = ""

            try:
                ai_first_message = ai_coach.start_review_session(
                    analysis_context=analysis_context,
                    trade_data=trade_summary,
                    ohlc_summary=ohlc_summary,
                    global_context=formatted_history
                )

                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': ai_first_message
                })

                # 儲存到資料庫
                db.add_chat_message(
                    session_id=st.session_state.session_id,
                    role='assistant',
                    content=ai_first_message
                )

            except Exception as e:
                st.error(f"AI 初始化失敗：{str(e)}")

        # 顯示對話歷史
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg['role']):
                st.write(msg['content'])

        # 使用者輸入
        user_input = st.chat_input("分享你當時的想法...")

        if user_input:
            # 加入使用者訊息
            st.session_state.chat_messages.append({
                'role': 'user',
                'content': user_input
            })

            db.add_chat_message(
                session_id=st.session_state.session_id,
                role='user',
                content=user_input
            )

            # 顯示使用者訊息
            with st.chat_message('user'):
                st.write(user_input)

            # 取得 AI 回應
            try:
                ai_response = ai_coach.continue_conversation(
                    chat_history=st.session_state.chat_messages[:-1],
                    user_message=user_input
                )

                st.session_state.chat_messages.append({
                    'role': 'assistant',
                    'content': ai_response
                })

                db.add_chat_message(
                    session_id=st.session_state.session_id,
                    role='assistant',
                    content=ai_response
                )

                # 顯示 AI 回應
                with st.chat_message('assistant'):
                    st.write(ai_response)

            except Exception as e:
                st.error(f"AI 回應失敗：{str(e)}")

        # 自動提取錯誤卡片功能
        st.markdown("### 🃏 錯誤管理")
        if st.button("✨ 自動偵測並建立錯誤卡片"):
            if len(st.session_state.chat_messages) < 2:
                st.warning("對話內容太少，無法進行分析。請先與 AI 教練多聊幾句。")
            else:
                with st.spinner("AI 正在分析對話中的交易失誤..."):
                    # 組合對話內容
                    full_conversation = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_messages])
                    
                    # 呼叫 AI 偵測
                    detected_mistakes = ai_coach.detect_mistakes(full_conversation)
                    
                    if detected_mistakes:
                        count = 0
                        for mistake in detected_mistakes:
                            # 嘗試從交易數據中獲取 PnL (取總盈虧作為估計)
                            pnl = trades_df['realized_pnl'].sum()
                            
                            db.add_mistake(
                                symbol=selected_symbol,
                                date=start_date,
                                error_type=mistake.get('error_type', 'Unknown'),
                                description=mistake.get('description', ''),
                                pnl=pnl,
                                ai_analysis=mistake.get('ai_analysis', '')
                            )
                            count += 1
                        
                        st.success(f"✅ 已成功建立 {count} 張錯誤卡片！請前往「🃏 錯誤卡片」頁面查看。")
                    else:
                        st.info("👍 AI 在本次對話中沒有偵測到明顯的典型交易錯誤。繼續保持！")

    # 6. 儲存日誌區
    st.markdown("---")
    st.subheader("📝 儲存交易日誌")

    with st.form("journal_form"):
        col1, col2 = st.columns(2)

        with col1:
            thesis = st.text_area(
                "交易論點 (Thesis)",
                placeholder="當時為什麼進場？技術面還是基本面？",
                height=100
            )

        with col2:
            mood = st.selectbox(
                "當時心情",
                ["😌 平靜", "😰 焦慮", "😤 激動", "😕 猶豫", "😎 自信"]
            )

        key_takeaway = st.text_area(
            "關鍵教訓 (Key Takeaway)",
            placeholder="從這次交易中學到了什麼？",
            height=100
        )

        submit_journal = st.form_submit_button("💾 儲存日誌", type="primary")

        if submit_journal:
            journal_id = db.add_journal_entry(
                trade_date=start_date,
                symbol=selected_symbol,
                thesis=thesis,
                mood=mood,
                key_takeaway=key_takeaway
            )

            st.success(f"✅ 日誌已儲存 (ID: {journal_id})")
            st.balloons()
