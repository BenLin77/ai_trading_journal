# 📊 AI 交易日誌系統

一個結合數據分析與 AI 教練的多頁面互動式交易檢討工具。

🆕 **已完整整合進階量化回測引擎**，實現專業級量化交易閉環！

**最新整合功能：**
- ✅ 百分位指標策略 (Percentile Indicators)
- ✅ 參數高原分析 (Parameter Plateau Detection) - 過擬合風險評估
- ✅ Coinbase API 整合 - 加密貨幣數據支援
- ✅ 向量化回測引擎 - 大幅提升運算效能
- ✅ 自動化批次回測 (JSON 配置驅動)

## ✨ 核心功能

### 1. 📤 主頁面 (Home)
- 上傳 IBKR 交易 CSV 報表
- 自動匯入並去重交易紀錄
- 系統狀態儀表板

### 2. 📈 交易檢討 (Review)
- 選擇標的和日期範圍
- 自動抓取 yfinance K 線數據
- Python 規則引擎偵測「追高」和「殺低」
- 整合 K 線圖與交易標記（Plotly 互動圖表）
- AI 教練對話介面（深度心理分析）
- 儲存交易日誌（論點、心情、教訓）

### 3. 🎯 策略實驗室 (Strategy)
- What-if 情境分析
- 自動抓取即時市價和 IV
- Python 策略引擎推薦（基於目標和 IV）
- AI 深度策略分析（比較優劣、風險收益）

### 4. 📊 績效成績單 (Report Card)
- 關鍵績效指標（KPI）
- 按標的分析盈虧
- 按時段分析盈虧（找出「魔鬼時刻」）
- AI 績效評語與改進建議

### 🆕 5. 🔬 策略實驗室 (Strategy Lab)
**專業級量化回測引擎**
- 多策略批次回測（MA、BB、HL、VALUE、Percentile）
- 參數高原視覺化（識別穩健參數區間）
- AI 過擬合風險評估與建議
- 向量化計算引擎（Numba JIT 加速）
- JSON 配置驅動的自動化回測
- 生成專業策略報告與視覺化儀表板

### 🆕 6. 💡 選擇權策略顧問
- 專為衍生性商品設計的 AI 顧問
- 根據市場看法推薦選擇權策略 (Spread, Iron Condor 等)
- 實時計算 Greeks 風險指標

### 🆕 7. 🧠 投資組合 AI 顧問 (Portfolio Advisor)
**最強大的整合功能**
- 自動載入資料庫中的實際持倉
- 讀取你的 Markdown 研究報告
- 抓取所有持倉的即時市場數據
- AI 綜合分析：風險評估、避險建議、部位調整
- **具體可執行的建議**（精確到口數、履約價、時機）

範例輸出：
> 建議立即執行避險：
> - 賣出 ONDS 20251220 Call $10 x 30口
> - 買入 ONDS 20251220 Put $6.5 x 20口
> - 預估成本：$XXX，保護範圍：$X.X
### 🆕 8. 🤖 自動化匯入 (n8n/CSV Integration)
- 支援透過 n8n 自動抓取交易資料並匯出為 CSV
- 支援在 `.env` 中設定 `AUTO_IMPORT_CSV_PATH` 實現自動載入
- 亦可隨時手動上傳 CSV 檔案

### 🆕 9. 🃏 錯誤卡片牆 (Mistake Cards)
- **自動偵測**：AI 教練會從對話中自動識別你的交易失誤（如凹單、追高）
- **卡片化管理**：將每次教訓轉化為卡片，記錄標的、代價與 AI 建議
- **PTT 整合**：一鍵生成 PTT [請益] 文模板，方便去股版找溫暖或討教
- **鄉民智慧**：內建 PTT 常見交易術語與錯誤知識庫

## 🛠️ 技術棧

### 前端與介面
- **前端框架**: Streamlit (多頁面應用)
- **視覺化**: Plotly + Dash (互動式儀表板)
- **圖表**: 即時 K 線、參數熱圖、資金曲線

### 數據處理與分析
- **數據處理**: Pandas + NumPy
- **效能優化**: Numba JIT 編譯 (向量化加速)
- **市場數據來源**:
  - yfinance (股票、ETF)
  - Coinbase API (加密貨幣)
  - Binance API (加密貨幣)
  - 本地 CSV 檔案

### 核心引擎
- **資料庫**: SQLite (交易記錄、回測結果)
- **AI 引擎**: Google Gemini API (深度分析與建議)
- **回測引擎**: 完整向量化引擎
  - 5 大策略系列 (MA、BB、HL、VALUE、Percentile)
  - 參數高原分析 (過擬合偵測)
  - 統計分析模組 (相關性、季節性、穩定性測試)

### 進階功能
- **衍生品支援**: 選擇權、期貨完整分析
- **自動化工作流**:
  - n8n (交易資料 -> CSV 自動匯入)
  - JSON 配置驅動批次回測
  - 自動化績效追蹤

## 📦 安裝步驟

### 1. 確認環境
```bash
# 確保已安裝 Python 3.9+ 和 uv
python --version
uv --version
```

### 2. 安裝依賴
```bash
# 使用 uv 安裝（推薦）
uv add streamlit pandas yfinance plotly google-generativeai python-dotenv

# 或使用 pip
pip install -r requirements.txt
```

### 3. 設定環境變數
```bash
# 複製範本
cp .env.example .env

# 編輯 .env 檔案，填入你的 Gemini API Key
# 取得 API Key: https://makersuite.google.com/app/apikey
```

## 🚀 啟動應用程式

```bash
# 使用 uv 執行
uv run streamlit run Home.py

# 或直接執行
streamlit run Home.py
```

應用程式將在瀏覽器中自動開啟（預設 http://localhost:8501）

## 📋 使用流程

### 步驟 1：上傳交易報表
1. 前往主頁面
2. 上傳 IBKR CSV 檔案
3. 確認欄位對應
4. 點擊「開始匯入」

**CSV 格式要求：**
- 必須包含：`DateTime`, `Symbol`, `Action`, `Quantity`, `Price`
- 可選：`Commission`, `Realized P/L`

### 步驟 2：交易檢討
1. 前往「📈 交易檢討」頁面
2. 選擇標的、日期範圍、K 線週期
3. 點擊「載入數據」
4. 查看圖表和 Python 規則引擎分析
5. 與 AI 教練對話
6. 儲存交易日誌

### 步驟 3：策略模擬
1. 前往「🎯 策略實驗室」頁面
2. 輸入標的代號
3. 點擊「抓取即時數據」
4. 填寫持倉和目標
5. 查看 Python 推薦和 AI 深度分析

### 步驟 4：績效分析
1. 前往「📊 績效成績單」頁面
2. 查看全局 KPI
3. 分析各標的和時段表現
4. 取得 AI 績效評語

### 🆕 步驟 5：專業級策略回測
**選項 A：互動式回測**
1. 前往「🔬 策略實驗室」頁面
2. 選擇數據來源（yfinance、Coinbase、Binance、本地檔案）
3. 選擇回測策略與參數範圍
4. 執行回測並即時查看結果
5. 使用參數高原分析找出最穩健參數

**選項 B：自動化批次回測**
1. 建立 JSON 配置檔案（範例見 `core/automation/`）
2. 執行自動化腳本：`uv run python run_backtest.py`
3. 載入回測結果到策略實驗室
4. 取得 AI 過擬合風險評估與建議

### 🆕 步驟 6：投資組合 AI 顧問
**最強大的整合功能 - 完整閉環**

1. **準備研究報告**：
   - 在 `reports/` 資料夾建立 Markdown 研究報告
   - 參考 `reports/EXAMPLE_Market_Analysis.md` 範本
   - 建議包含：市場分析、個股研判、風險提示、操作建議

2. **執行 AI 分析**：
   - 前往「🧠 投資組合 AI 顧問」頁面
   - 系統自動載入資料庫中的持倉
   - 選擇要納入的研究報告
   - 點擊「更新所有持倉的即時數據」
   - 執行「AI 深度分析」

3. **取得具體建議**：
   - 風險評估（集中度、方向性、時間風險）
   - 避險建議（精確到標的、口數、履約價）
   - 部位調整建議（加倉/減倉/觀望）
   - 風險監控指標（停損/停利價位）

4. **執行操作**：
   - 根據 AI 建議執行交易
   - 定期更新（建議每日收盤後檢視一次）

## 📁 專案結構

```
ai_trading_journal/
├── Home.py                      # 主頁面（CSV 上傳與欄位自動對應）
├── database.py                  # SQLite 資料庫管理（支援衍生品）
├── run_backtest.py              # 自動化回測執行腳本
│
├── pages/                       # Streamlit 多頁面應用
│   ├── 1_Review.py             # 交易檢討（K 線 + AI 教練）
│   ├── 2_Strategy.py           # 策略模擬（What-if 分析）
│   ├── 3_Report_Card.py        # 績效成績單（KPI 儀表板）
│   ├── 4_Strategy_Lab.py       # 策略回測實驗室
│   ├── 5_Options_Strategy.py  # 選擇權策略顧問
│   └── 6_Portfolio_Advisor.py # 🆕 投資組合 AI 顧問
│
├── utils/                       # 前端工具模組
│   ├── analysis.py             # 交易行為分析引擎
│   ├── charts.py               # Plotly 圖表生成器
│   ├── ai_coach.py             # AI 對話與分析
│   ├── ai_strategy_advisor.py  # AI 策略建議
│   ├── backtest_loader.py      # 回測結果載入器
│   ├── derivatives_support.py  # 衍生品解析工具
│   └── export.py               # 數據匯出功能
│
├── core/                        # 🆕 完整量化回測引擎
│   ├── engine.py               # 主引擎入口
│   ├── backtest_engine/        # 回測核心模組
│   │   ├── Base_backtester.py
│   │   ├── VectorBacktestEngine_backtester.py  # 向量化引擎
│   │   ├── Indicators_backtester.py            # 指標基類
│   │   ├── MovingAverage_Indicator_backtester.py
│   │   ├── BollingerBand_Indicator_backtester.py
│   │   ├── HL_Indicator_backtester.py
│   │   ├── VALUE_Indicator_backtester.py
│   │   ├── Percentile_Indicator_backtester.py  # 🆕 百分位指標
│   │   ├── TradeSimulator_backtester.py
│   │   └── SpecMonitor_backtester.py
│   │
│   ├── data_feed/              # 數據來源模組
│   │   ├── base_loader.py
│   │   ├── yfinance_loader.py
│   │   ├── binance_loader.py
│   │   ├── coinbase_loader.py  # 🆕 Coinbase API
│   │   ├── file_loader.py
│   │   ├── validator_loader.py
│   │   └── calculator_loader.py
│   │
│   ├── performance_metrics/    # 績效指標模組
│   │   ├── MetricsCalculator_metricstracker.py
│   │   └── MetricsExporter_metricstracker.py
│   │
│   ├── analytics/              # 統計分析模組
│   │   ├── StationarityTest_statanalyser.py
│   │   ├── CorrelationTest_statanalyser.py
│   │   ├── SeasonalAnalysis_statanalyser.py
│   │   └── ReportGenerator_statanalyser.py
│   │
│   ├── visualization/          # 視覺化模組
│   │   ├── DashboardGenerator_plotter.py
│   │   ├── ParameterPlateau_plotter.py  # 🆕 參數高原分析
│   │   ├── ChartComponents_plotter.py
│   │   └── MetricsDisplay_plotter.py
│   │
│   └── automation/             # 自動化模組
│       ├── ConfigLoader_autorunner.py
│       ├── BacktestRunner_autorunner.py
│       └── SwitchDataSource_autorunner.py
│
├── reports/                     # 🆕 研究報告資料夾
│   ├── README.md               # 使用說明
│   └── EXAMPLE_Market_Analysis.md  # 範例報告
│
├── .env.example                # 環境變數範本
├── .gitignore                  # Git 忽略設定
├── requirements.txt            # Python 依賴清單
└── README.md                   # 本文件
```

## 🗄️ 資料庫架構

### Trades (交易表)
- `trade_id`: 唯一交易 ID (防重複)
- `datetime`: 交易時間
- `symbol`: 標的代號
- `action`: 買賣動作
- `quantity`: 數量
- `price`: 價格
- `commission`: 手續費
- `realized_pnl`: 已實現盈虧

### Journal (日誌表)
- `journal_id`: 日誌 ID
- `trade_date`: 交易日期
- `symbol`: 標的代號
- `thesis`: 交易論點
- `mood`: 心情
- `key_takeaway`: 關鍵教訓

### Chat_History (對話表)
- `message_id`: 訊息 ID
- `session_id`: 會話 ID
- `role`: 角色 (user/assistant)
- `content`: 內容
- `timestamp`: 時間戳

## ⚙️ 核心邏輯

### Python 規則引擎 (analysis.py)
- **追高偵測**: 買價接近 K 棒最高點（閾值 2%）
- **殺低偵測**: 賣價接近 K 棒最低點（閾值 2%）
- **時段分析**: 按小時統計盈虧

### AI 教練 (ai_coach.py)
使用 Google Gemini API，提供：
1. **交易檢討**: 基於 Python 偵測結果，引導反思
2. **策略建議**: 比較選擇權策略，考慮 IV 影響
3. **績效評語**: 診斷核心問題，提出改進建議

## 🆕 進階量化功能詳解

### 1. 百分位指標策略 (Percentile Indicators)
**6 種細分策略**，基於滾動百分位動態閾值：
- **PERC1**: 價格升穿 m 百分位做多
- **PERC2**: 價格升穿 m 百分位做空（反向）
- **PERC3**: 價格跌破 m 百分位做多（抄底）
- **PERC4**: 價格跌破 m 百分位做空
- **PERC5**: 價格在 m1-m2 百分位區間做多（震盪策略）
- **PERC6**: 價格在 m1-m2 百分位區間做空

**效能優化**：
- Numba JIT 編譯加速（提升 10-50 倍效能）
- 向量化批次計算（支援大規模參數掃描）

### 2. 參數高原分析 (Parameter Plateau Detection)
**識別穩健參數區間，避免過擬合**：

**工作原理**：
1. 執行大規模參數掃描（例如：window 10-200、threshold 1-10）
2. 計算每組參數的績效指標（Sharpe、勝率、MDD）
3. 視覺化熱圖，識別「高原區域」
4. AI 分析建議最穩健參數範圍

**判斷標準**：
- ✅ **穩健參數**：績效在鄰近參數組合間變化小（高原）
- ⚠️ **過擬合參數**：績效在鄰近參數組合間劇烈變化（孤峰）

### 3. 向量化回測引擎
**核心優勢**：
- **批次計算**: 一次執行數千組參數組合
- **記憶體優化**: 智慧快取機制，避免重複計算
- **並行處理**: 充分利用 CPU 資源
- **效能提升**: 相較傳統迴圈快 50-100 倍

### 4. 多數據源整合
**支援 4 種數據來源**：
1. **yfinance**: 全球股票、ETF（免費、即時）
2. **Coinbase API**: 加密貨幣（BTC、ETH 等）
3. **Binance API**: 加密貨幣（更多交易對）
4. **本地 CSV**: 自訂數據格式

### 5. 自動化批次回測
**JSON 配置驅動**，無需編程：
```json
{
  "symbol": "AAPL",
  "data_source": "yfinance",
  "strategies": ["MA", "BB", "Percentile"],
  "parameter_ranges": {
    "window": [10, 20, 50, 100],
    "threshold": [1.0, 1.5, 2.0]
  }
}
```

執行：
```bash
uv run python run_backtest.py --config backtest_config.json
```

## 🔒 安全注意事項

- ✅ `.env` 已加入 `.gitignore`
- ✅ 資料庫檔案 (*.db) 已加入 `.gitignore`
- ✅ 永不提交 API Keys 到版本控制
- ⚠️ 本地執行，數據不會上傳至雲端

## 🐛 常見問題

### Q: AI 功能無法使用？
**A**: 確認 `.env` 檔案中已設定 `GEMINI_API_KEY`

### Q: K 線數據抓取失敗？
**A**: 確認標的代號正確（使用美股代號，例如 AAPL）

### Q: CSV 匯入失敗？
**A**: 檢查 CSV 檔案格式，確保包含必要欄位

### Q: 資料庫檔案在哪裡？
**A**: 預設在專案根目錄下的 `trading_journal.db`

## 📚 進階使用

### 自訂分析閾值
編輯 `pages/1_Review.py`：
```python
analyzer = TradingAnalyzer(threshold=0.03)  # 改為 3%
```

### 修改 K 線週期選項
編輯 `pages/1_Review.py`：
```python
interval = st.selectbox(
    "K 線週期",
    ['1m', '5m', '15m', '30m', '1h', '1d', '1wk'],  # 新增 1wk
    index=1
)
```

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

## 📄 授權

MIT License

## 🙏 致謝

- Streamlit: 快速建立數據應用
- yfinance: 市場數據來源
- Plotly: 互動式圖表
- Google Gemini: AI 能力
