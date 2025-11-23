"""
AI 交易日誌系統 - 主頁面

系統入口與 CSV 檔案上傳功能
"""

import streamlit as st
import pandas as pd
from database import TradingDatabase
from datetime import datetime
from utils.derivatives_support import InstrumentParser
from pathlib import Path
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 頁面配置
st.set_page_config(
    page_title="AI 交易日誌",
    page_icon="📊",
    layout="wide"
)

# 初始化資料庫（確保資料庫已建立）
@st.cache_resource
def init_db():
    """初始化資料庫連接"""
    return TradingDatabase()

db = init_db()

# 主標題
st.title("📊 AI 交易日誌系統")
st.markdown("---")

# 歡迎訊息
st.markdown("""
### 歡迎使用 AI 交易日誌系統

這是一個結合數據分析與 AI 教練的交易檢討工具。你可以：

- 📤 **上傳交易紀錄**：匯入 IBKR CSV 報表
- 📈 **檢討交易**：與 AI 教練對話，深度分析每筆交易
- 🎯 **策略模擬**：What-if 情境分析與選擇權策略建議
- 📊 **績效分析**：長期績效追蹤與改進建議

請先上傳你的交易報表開始使用。
""")

st.markdown("---")

# 檢查是否設定自動匯入路徑
auto_csv_path = os.getenv('AUTO_IMPORT_CSV_PATH', '').strip()

df = None
data_source = None

# 自動載入模式
if auto_csv_path and Path(auto_csv_path).exists():
    st.header("📥 自動 CSV 匯入")

    file_info = Path(auto_csv_path)
    st.success(f"✅ 已設定自動匯入：`{auto_csv_path}`")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("檔案名稱", file_info.name)
    with col2:
        file_size_mb = file_info.stat().st_size / 1024 / 1024
        st.metric("檔案大小", f"{file_size_mb:.2f} MB")
    with col3:
        mod_time = datetime.fromtimestamp(file_info.stat().st_mtime)
        st.metric("最後更新", mod_time.strftime('%Y-%m-%d %H:%M'))

    if st.button("🔄 重新載入 CSV", type="primary"):
        try:
            df = pd.read_csv(auto_csv_path)
            data_source = "auto"
            st.success(f"✅ 成功載入 {len(df)} 筆記錄")
        except Exception as e:
            st.error(f"❌ 載入失敗：{str(e)}")

    st.info("""
    **自動匯入模式已啟用**
    - 系統會從 `.env` 設定的路徑自動載入 CSV
    - 點擊「重新載入 CSV」更新資料
    - 如需手動上傳，請移除 `.env` 中的 `AUTO_IMPORT_CSV_PATH` 設定
    """)

# 手動上傳模式
else:
    st.header("📤 上傳 IBKR 交易報表")

    st.info("""
    **CSV 檔案格式要求：**
    - 必須包含欄位：`Date`、`Symbol`、`Side`、`Quantity`、`Price`
    - 可選欄位：`Commission`、選擇權欄位（`Strike`、`Expiry`、`Right`）
    - **支援來源**：IBKR 官方報表、n8n 自動生成報表

    如果你的 CSV 欄位名稱不同，系統會嘗試自動對應。

    💡 **提示**：如需自動載入，請在 `.env` 設定 `AUTO_IMPORT_CSV_PATH`
    """)

    uploaded_file = st.file_uploader(
        "選擇 CSV 檔案",
        type=['csv'],
        help="請選擇從 IBKR 下載的交易報表 CSV 檔案，或 n8n 自動生成的匯總報表"
    )

    if uploaded_file is not None:
        try:
            # 讀取 CSV
            df = pd.read_csv(uploaded_file)
            data_source = "manual"

            st.success(f"✅ 成功讀取檔案，共 {len(df)} 筆交易紀錄")

            # 資料驗證
            if len(df) == 0:
                st.error("❌ CSV 檔案是空的，請檢查檔案內容")
                st.stop()

            if len(df.columns) < 5:
                st.warning(f"⚠️ CSV 只有 {len(df.columns)} 個欄位，可能缺少必要欄位")
        except Exception as e:
            st.error(f"❌ 檔案讀取錯誤：{str(e)}")
            st.stop()

# 共用處理邏輯（自動載入和手動上傳都會執行）
if df is not None:
    # 顯示原始數據預覽與統計
    with st.expander("📋 查看原始數據與統計", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("總筆數", len(df))
        with col2:
            st.metric("欄位數", len(df.columns))
        with col3:
            # 檢測可能的重複
            potential_duplicates = df.duplicated().sum()
            st.metric("可能重複", potential_duplicates)

        st.dataframe(df.head(10), use_container_width=True)

        # 數據品質檢查
        st.write("**數據品質檢查：**")
        missing_values = df.isnull().sum()
        if missing_values.sum() > 0:
            st.warning(f"發現 {missing_values.sum()} 個空值")
            st.write(missing_values[missing_values > 0])

    # 欄位對應（自動偵測）
    st.subheader("🔄 欄位對應")

    # 自動偵測欄位名稱
    def find_column(possible_names, columns):
        """根據可能的名稱列表找到對應欄位"""
        for name in possible_names:
            for col in columns:
                if name.lower() in col.lower():
                    return list(columns).index(col)
        return 0

    datetime_idx = find_column(['datetime', 'date', 'time'], df.columns)
    symbol_idx = find_column(['symbol', 'ticker'], df.columns)
    action_idx = find_column(['action', 'side', 'type'], df.columns)
    quantity_idx = find_column(['quantity', 'qty', 'amount'], df.columns)
    price_idx = find_column(['price', 'fill', 'avg'], df.columns)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**CSV 欄位**")
        datetime_col = st.selectbox("日期時間欄位", df.columns, index=datetime_idx)
        symbol_col = st.selectbox("標的代號欄位", df.columns, index=symbol_idx)
        action_col = st.selectbox("買賣動作欄位", df.columns, index=action_idx)

    with col2:
        st.write("**對應目標**")
        quantity_col = st.selectbox("數量欄位", df.columns, index=quantity_idx)
        price_col = st.selectbox("價格欄位", df.columns, index=price_idx)

        # 可選欄位
        commission_col = st.selectbox(
            "手續費欄位（可選）",
            ['無'] + list(df.columns),
            index=list(df.columns).index('Commission') + 1 if 'Commission' in df.columns else 0
        )
        pnl_col = st.selectbox(
            "已實現盈虧欄位（可選）",
            ['無'] + list(df.columns),
            index=0
        )

    # 選擇權欄位（如果有的話）
    st.write("**選擇權欄位（如適用）**")
    col3, col4 = st.columns(2)
    with col3:
        strike_col = st.selectbox(
            "履約價欄位（可選）",
            ['無'] + list(df.columns),
            index=list(df.columns).index('Strike') + 1 if 'Strike' in df.columns else 0
        )
        expiry_col = st.selectbox(
            "到期日欄位（可選）",
            ['無'] + list(df.columns),
            index=list(df.columns).index('Expiry') + 1 if 'Expiry' in df.columns else 0
        )
    with col4:
        right_col = st.selectbox(
            "權利類型欄位（可選）",
            ['無'] + list(df.columns),
            index=list(df.columns).index('Right') + 1 if 'Right' in df.columns else 0
        )

        # 匯入按鈕
        if st.button("🚀 開始匯入", type="primary"):
            # 建立進度指示器
            progress_bar = st.progress(0)
            status_text = st.empty()

            new_count = 0
            duplicate_count = 0
            error_count = 0
            total = len(df)

            for idx, row in df.iterrows():
                # 更新進度
                progress = (idx + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"處理中... {idx + 1}/{total} ({progress*100:.1f}%)")

                try:
                    symbol = str(row[symbol_col]).strip()

                    # 如果有分散的選擇權欄位，先合併成完整符號
                    if strike_col != '無' and not pd.isna(row[strike_col]) and row[strike_col]:
                        # 有選擇權資訊，需要合併
                        underlying = symbol.split()[0]  # 取第一個詞作為標的
                        strike = str(row[strike_col]).strip()
                        expiry = str(row[expiry_col]).strip() if expiry_col != '無' else ''
                        right = str(row[right_col]).strip() if right_col != '無' else ''

                        # 清理到期日格式（移除重複的權利類型）
                        if right and right in expiry:
                            expiry = expiry.replace(right, '').strip()

                        # 組合完整符號：例如 "ONDS 251114C8" 或 "ONDS 20251114C8"
                        if expiry and right:
                            symbol = f"{underlying} {expiry}{strike}"
                        elif expiry:
                            symbol = f"{underlying} {expiry}"

                    # 解析標的類型（股票/選擇權/期貨）
                    parsed = InstrumentParser.parse_symbol(symbol)

                    trade_data = {
                        'datetime': str(row[datetime_col]),
                        'symbol': symbol,
                        'action': str(row[action_col]).upper(),  # 統一大寫
                        'quantity': float(row[quantity_col]),
                        'price': float(row[price_col]),
                        'commission': float(row[commission_col]) if commission_col != '無' and not pd.isna(row[commission_col]) else 0,
                        'realized_pnl': float(row[pnl_col]) if pnl_col != '無' and not pd.isna(row[pnl_col]) else 0,
                        'instrument_type': parsed['instrument_type'],
                        'underlying': parsed['underlying'],
                        'strike': parsed['strike'],
                        'expiry': parsed['expiry'],
                        'option_type': parsed['option_type'],
                        'multiplier': parsed['multiplier']
                    }

                    # 嘗試新增（避免重複）
                    if db.add_trade(trade_data):
                        new_count += 1
                    else:
                        duplicate_count += 1

                except Exception as e:
                    error_count += 1
                    if error_count == 1:  # 只顯示第一個錯誤
                        st.warning(f"第 {idx + 1} 筆數據處理失敗：{str(e)}")

            # 清除進度指示
            progress_bar.empty()
            status_text.empty()

            # 顯示結果
            st.success(f"✅ 匯入完成！")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("新增交易", f"{new_count} 筆", delta_color="normal")
            col2.metric("重複交易", f"{duplicate_count} 筆", delta_color="off")
            col3.metric("錯誤數", f"{error_count} 筆", delta_color="inverse")
            col4.metric("成功率", f"{(new_count/(new_count+error_count)*100 if new_count+error_count > 0 else 0):.1f}%")

            if error_count > 0:
                st.warning(f"⚠️ 有 {error_count} 筆數據無法匯入，請檢查 CSV 格式")

            st.balloons()


# 側邊欄：系統狀態
with st.sidebar:
    st.header("📊 系統狀態")

    # 顯示資料庫統計
    stats = db.get_trade_statistics()
    symbols = db.get_all_symbols()

    st.metric("總交易筆數", stats.get('total_trades', 0))
    st.metric("交易標的數", len(symbols))
    st.metric("總盈虧", f"${stats.get('total_pnl', 0):,.2f}")

    st.markdown("---")

    st.markdown("""
    ### 🚀 快速導航

    - [📈 交易檢討](pages/1_Review.py)
    - [🎯 策略實驗室 (模擬)](pages/2_Strategy.py)
    - [📊 績效成績單](pages/3_Report_Card.py)
    - [🔬 策略回測 (Core)](pages/4_Strategy_Lab.py)
    - [💡 選擇權顧問](pages/5_Options_Strategy.py)
    - [🃏 錯誤卡片](pages/7_Mistake_Cards.py)
    """)

    st.markdown("---")

    st.caption("💡 提示：先上傳交易報表，然後前往各功能頁面進行分析。")
