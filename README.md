# 📊 AI Trading Journal

一個結合數據分析與 AI 教練的專業級交易檢討與投資組合管理系統。

> **架構**: Next.js 前端 + FastAPI 後端，完全分離的現代化架構

## ✨ 核心功能

### 📈 儀表板 (Dashboard)
- 帳戶總覽與 KPI 指標
- 累計盈虧曲線
- 持倉概覽與策略識別
- IBKR Flex Query 自動同步

### 📋 交易檢討 (Trade Review)
- 按標的瀏覽交易記錄
- AI 對話式交易分析
- 規則引擎偵測「追高」「殺低」

### 📔 交易日誌 (Trading Journal) 🆕
#### MFE/MAE 分析
- 計算每筆交易的最大浮盈 (MFE) 和最大浮虧 (MAE)
- 評估交易效率（抓住多少潛在利潤）
- 視覺化 MFE/MAE 分布圖（類似選擇權損益圖風格）
- AI 分析交易執行品質並給出改進建議

#### 交易計劃 (Trade Plans)
- 建立交易前計劃（進場條件、目標價、停損價）
- 自動計算風險報酬比
- AI 評價計劃可行性
- 連結實際交易進行事後分析
- 比較「計劃 vs 實際」差異

#### 日誌筆記 (Notes)
- 每日/每週/每月交易日誌
- 情緒狀態追蹤
- 信心水平記錄
- 關鍵觀察與教訓
- AI 分析筆記內容並給出建議

### 🎯 策略模擬 (Strategy Simulation)
- What-if 情境分析
- 股票/選擇權/期貨支援
- Python 策略引擎推薦
- AI 深度策略分析

### 📊 績效成績單 (Performance Report)
- 關鍵績效指標（勝率、獲利因子等）
- 標的盈虧排行
- 時段盈虧分析（找出魔鬼時刻）
- AI 績效評語與改進建議

### 🔬 策略實驗室 (Strategy Lab)
- 載入回測結果分析
- 參數高原視覺化
- 過擬合風險評估
- AI 策略建議

### 💡 選擇權 AI 顧問 (Options Advisor)
- 根據市場看法推薦策略
- 支援 Bullish/Bearish/Neutral/Volatile
- Greeks 風險說明
- 精確的履約價建議

### 🧠 Portfolio AI 顧問
- 自動載入實際持倉
- 讀取 Markdown 研究報告
- 抓取即時市場數據
- AI 綜合風險評估與避險建議
- **AI 綜合審查**：整合 MFE/MAE、交易計劃和日誌進行全面分析

### 🎴 錯誤卡片 (Mistake Cards)
- 記錄交易失誤與教訓
- 情緒狀態追蹤
- 錯誤類型統計
- 成長回顧

## 🛠️ 技術架構

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)                │
│   React 19 + TypeScript + TailwindCSS + React Query     │
└─────────────────────────┬───────────────────────────────┘
                          │ REST API
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                     │
│   Python + SQLite + Gemini AI + IBKR Flex Query         │
└─────────────────────────────────────────────────────────┘
```

### Frontend
- **框架**: Next.js 15 (App Router)
- **語言**: TypeScript
- **UI**: React 19 + TailwindCSS
- **狀態**: Zustand + React Query
- **圖表**: (待整合 Plotly/Recharts)

### Backend
- **框架**: FastAPI (Python)
- **資料庫**: SQLite
- **AI**: Google Gemini API
- **數據**: yfinance + IBKR Flex Query

## 📦 快速開始

### 1. 環境需求
```bash
# Python 3.10+
python --version

# Node.js 20+ (Next.js 16 需要)
node --version
# 如果版本不對，使用 nvm 切換:
# nvm install 20 && nvm use 20

# uv (Python 套件管理)
uv --version
```

### 2. 安裝依賴
```bash
# 後端 (Python)
uv sync

# 前端 (Node.js)
cd frontend && npm install
```

### 3. 設定環境變數
```bash
# 複製範本
cp .env.example .env

# 編輯 .env 檔案，填入：
# - GEMINI_API_KEY: Google Gemini API Key
# - IBKR_FLEX_TOKEN: IBKR Flex Query Token (可選)
# - IBKR_HISTORY_QUERY_ID: 交易歷史 Query ID (可選)
# - IBKR_POSITIONS_QUERY_ID: 持倉 Query ID (可選)
```

### 4. 啟動開發伺服器
```bash
# 同時啟動前後端
./run-dev.sh

# 或分別啟動：
# 後端
cd backend && uv run uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```

### 5. 開啟應用
- **前端**: http://localhost:3000
- **API 文檔**: http://localhost:8000/docs

## 📁 專案結構

```
ai_trading_journal/
├── backend/                    # FastAPI 後端
│   └── main.py                # API 端點
│
├── frontend/                   # Next.js 前端
│   ├── src/
│   │   ├── app/              # 頁面路由
│   │   │   ├── page.tsx      # 儀表板
│   │   │   ├── review/       # 交易檢討
│   │   │   ├── strategy/     # 策略模擬
│   │   │   ├── report/       # 績效報告
│   │   │   ├── lab/          # 策略實驗室
│   │   │   ├── options/      # 選擇權顧問
│   │   │   ├── ai/           # Portfolio AI
│   │   │   ├── mistakes/     # 錯誤卡片
│   │   │   └── settings/     # 設定
│   │   ├── components/       # React 元件
│   │   └── lib/              # 工具函式
│   └── package.json
│
├── core/                       # 量化回測引擎
│   ├── engine.py              # 主引擎入口
│   ├── backtest_engine/       # 回測核心
│   ├── data_feed/             # 數據來源
│   ├── analytics/             # 統計分析
│   └── visualization/         # 視覺化
│
├── utils/                      # 共用工具
│   ├── ai_coach.py            # AI 對話引擎
│   ├── analysis.py            # 交易分析
│   ├── charts.py              # 圖表生成
│   └── ...
│
├── config/                     # 配置
├── database.py                 # 資料庫 ORM
├── reports/                    # 研究報告
├── docs/                       # 文件
│
├── .env.example               # 環境變數範本
├── .gitignore                 # Git 忽略設定
├── pyproject.toml             # Python 依賴
└── run-dev.sh                 # 開發啟動腳本
```

## 🔌 API 端點

### 交易相關
- `GET /api/trades` - 取得交易記錄
- `GET /api/trades/symbols` - 取得所有標的
- `GET /api/statistics` - 取得交易統計
- `GET /api/equity-curve` - 取得資金曲線

### 持倉相關
- `GET /api/portfolio` - 取得持倉總覽
- `POST /api/ibkr/sync` - 同步 IBKR 數據
- `GET /api/ibkr/cash` - 取得現金餘額

### AI 功能
- `POST /api/ai/chat` - AI 對話
- `POST /api/report/ai-review` - AI 績效評語
- `POST /api/strategy/ai-advice` - AI 策略建議
- `POST /api/options/advice` - AI 選擇權建議
- `POST /api/portfolio/ai-analysis` - AI 投資組合分析

### 其他
- `GET /api/report/performance` - 績效報告
- `GET /api/lab/backtests` - 列出回測結果
- `GET /api/mistakes` - 取得錯誤卡片
- `GET /api/market/quote/{symbol}` - 取得即時報價

完整 API 文檔請訪問: http://localhost:8000/docs

## 🔒 安全注意事項

- ✅ `.env` 已加入 `.gitignore`
- ✅ 資料庫檔案 (*.db) 已加入 `.gitignore`
- ✅ 永不提交 API Keys 到版本控制
- ⚠️ 本地執行，數據不會上傳至雲端

### 🔐 登入認證

系統預設啟用登入認證，用戶資訊存儲在資料庫中。

**預設帳號：**
| 欄位 | 值 |
|------|-----|
| 用戶名 | `ben` (不區分大小寫) |
| 密碼 | `!Trade346` |

**修改密碼：**
1. 登入系統後進入「設定」頁面
2. 找到「帳戶安全」區塊
3. 輸入目前密碼和新密碼
4. 點擊「修改密碼」

**環境變數：**
```bash
# 可選：初次啟動時使用的預設密碼
DEFAULT_USER_PASSWORD=!Trade346

# 可選：JWT 加密密鑰（建議在生產環境設定）
JWT_SECRET=your-secret-key
```


## 🐛 常見問題

### Q: AI 功能無法使用？
**A**: 確認 `.env` 檔案中已設定 `GEMINI_API_KEY`

### Q: 前端無法連接後端？
**A**: 確認後端已啟動在 port 8000，並檢查 CORS 設定

### Q: IBKR 同步失敗？
**A**: 確認已設定 `IBKR_FLEX_TOKEN` 和對應的 Query ID

### Q: 資料庫在哪裡？
**A**: 預設在專案根目錄下的 `trading_journal.db`

## 📄 授權

MIT License

## 🙏 致謝

- Next.js & React: 現代化前端框架
- FastAPI: 高效能 Python API 框架
- yfinance: 市場數據來源
- Google Gemini: AI 能力
- TailwindCSS: 美觀的 UI 樣式
