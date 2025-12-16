# AI Trading Journal - 功能規格說明書

> **版本**: 2.0.0  
> **最後更新**: 2024-12-16  
> **文件目的**: 提供詳細的功能說明，可供 AI 測試工具和人類開發者參考

---

## 目錄

1. [系統架構概述](#1-系統架構概述)
2. [儀表板 (Dashboard)](#2-儀表板-dashboard)
3. [交易檢討 (Trade Review)](#3-交易檢討-trade-review)
4. [交易日誌 (Trading Journal)](#4-交易日誌-trading-journal)
5. [策略模擬 (Strategy Simulation)](#5-策略模擬-strategy-simulation)
6. [績效報告 (Performance Report)](#6-績效報告-performance-report)
7. [策略實驗室 (Strategy Lab)](#7-策略實驗室-strategy-lab)
8. [選擇權顧問 (Options Advisor)](#8-選擇權顧問-options-advisor)
9. [Portfolio AI 顧問](#9-portfolio-ai-顧問)
10. [錯誤卡片 (Mistake Cards)](#10-錯誤卡片-mistake-cards)
11. [設定 (Settings)](#11-設定-settings)
12. [IBKR 整合](#12-ibkr-整合)
13. [AI 功能](#13-ai-功能)
14. [API 端點完整清單](#14-api-端點完整清單)
15. [資料庫結構](#15-資料庫結構)
16. [測試用例](#16-測試用例)

---

## 1. 系統架構概述

### 1.1 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| **前端框架** | Next.js (App Router) | 15.x |
| **前端語言** | TypeScript | 5.x |
| **UI 框架** | React | 19.x |
| **樣式** | TailwindCSS | 3.x |
| **狀態管理** | Zustand + React Query | 最新 |
| **後端框架** | FastAPI | 最新 |
| **後端語言** | Python | 3.10+ |
| **資料庫** | SQLite | 3.x |
| **AI 服務** | Google Gemini / DeepSeek / OpenAI | 視設定 |
| **市場數據** | yfinance | 最新 |
| **券商整合** | IBKR Flex Query | v3 |

### 1.2 資料流

```
[IBKR] --> Flex Query API --> [Backend] --> SQLite
                                  |
[Frontend] <-- REST API <-- [Backend] <-- [Gemini AI]
                                  |
                            [yfinance] --> Market Data
```

### 1.3 主要目錄

```
ai_trading_journal/
├── backend/main.py        # FastAPI 後端 (~3300 行)
├── database.py            # SQLite ORM (~1850 行)
├── frontend/src/app/      # Next.js 頁面
├── utils/                 # 工具模組
│   ├── ibkr_flex_query.py # IBKR 整合
│   ├── ai_coach.py        # AI 對話引擎
│   ├── option_strategies.py # 選擇權策略識別
│   └── validators.py      # 資料驗證
└── docs/                  # 文件
```

---

## 2. 儀表板 (Dashboard)

### 2.1 功能概述

儀表板是應用程式的主頁面，提供帳戶總覽和關鍵指標。

### 2.2 前端路由

- **路徑**: `/` (page.tsx)
- **元件**: `KPICards`, `EquityChart`, `PortfolioOverview`

### 2.3 主要功能

#### 2.3.1 KPI 指標卡片

顯示的指標：
- **總交易數** (total_trades)
- **總盈虧** (total_pnl)
- **勝率** (win_rate) - 百分比
- **獲利因子** (profit_factor)
- **最佳交易** (best_trade)
- **最差交易** (worst_trade)
- **現金餘額** (cash_balance)

**API 端點**:
```
GET /api/statistics?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

**回應格式**:
```json
{
  "total_trades": 150,
  "total_pnl": 12500.50,
  "win_rate": 65.5,
  "avg_win": 350.25,
  "avg_loss": -180.75,
  "profit_factor": 2.15,
  "best_trade": 2500.00,
  "worst_trade": -980.00
}
```

#### 2.3.2 資金曲線圖 (Equity Curve)

- **顯示**: 累計盈虧隨時間變化
- **X 軸**: 日期
- **Y 軸**: 累計盈虧金額

**API 端點**:
```
GET /api/equity-curve?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

**回應格式**:
```json
[
  {"date": "2024-01-15", "cumulative_pnl": 1250.50},
  {"date": "2024-01-16", "cumulative_pnl": 1500.75}
]
```

#### 2.3.3 持倉總覽 (Portfolio Overview)

顯示當前持倉，包含：
- **股票持倉**: 數量、均價、現價、未實現盈虧
- **選擇權持倉**: 策略識別（Covered Call、Iron Condor 等）
- **策略風險等級**: Low / Medium / High / Very High
- **現金餘額**: 帳戶可用現金

**API 端點**:
```
GET /api/portfolio
```

**回應格式**:
```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "underlying": "AAPL",
      "quantity": 100,
      "avg_cost": 175.50,
      "current_price": 180.25,
      "market_value": 18025.00,
      "unrealized_pnl": 475.00,
      "unrealized_pnl_pct": 2.71,
      "strategy": "Covered Call",
      "strategy_description": "持有 100 股 AAPL，賣出 1 張 Call",
      "risk_level": "Medium",
      "options": [
        {
          "symbol": "AAPL 241220C185",
          "option_type": "call",
          "strike": 185.0,
          "expiry": "2024-12-20",
          "quantity": 1,
          "action": "sell"
        }
      ]
    }
  ],
  "total_market_value": 125000.00,
  "total_unrealized_pnl": 3500.00,
  "total_realized_pnl": 8500.00,
  "cash_balance": 25000.00
}
```

#### 2.3.4 日期範圍選擇器

- **快捷選項**: MTD (本月)、1M、3M、YTD、1Y、ALL
- **自訂範圍**: 日期選擇器

#### 2.3.5 價格自動更新

- **更新頻率**: 每 60 秒
- **價格來源**: Yahoo Finance (yfinance) - **非 IBKR**
- **技術實現**: 
  - 前端 React Query `refetchInterval: 60000`
  - 後端調用 `_fetch_realtime_prices()` 從 yfinance 獲取
- **顯示**: 右上角顯示「價格更新於 HH:MM:SS」
- **注意**: 選擇權價格依賴 IBKR 快照，不會即時更新

### 2.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| DASH-001 | 載入儀表板 | 所有 KPI 卡片顯示數值 |
| DASH-002 | 日期篩選 | 資金曲線根據日期更新 |
| DASH-003 | 持倉顯示 | 顯示當前所有持倉 |
| DASH-004 | 策略識別 | 正確識別 Covered Call 等策略 |
| DASH-005 | 價格自動更新 | 60 秒後價格刷新 |
| DASH-006 | 現金餘額顯示 | 顯示正確的現金水位 |

---

## 3. 交易檢討 (Trade Review)

### 3.1 功能概述

提供按標的瀏覽交易記錄，並透過 AI 對話分析交易行為。

### 3.2 前端路由

- **路徑**: `/review`
- **元件**: 標的選擇器、K線圖、交易列表、AI 對話

### 3.3 主要功能

#### 3.3.1 標的選擇器

**API 端點**:
```
GET /api/trades/symbols
```

**回應格式**:
```json
["AAPL", "GOOGL", "NVDA", "SPY"]
```

#### 3.3.2 K 線圖與買賣點

**API 端點**:
```
GET /api/review/chart/{underlying}?period=1y
```

**回應格式**:
```json
{
  "symbol": "AAPL",
  "ohlc": [
    {
      "date": "2024-01-15",
      "open": 175.50,
      "high": 178.25,
      "low": 174.80,
      "close": 177.50,
      "volume": 52000000
    }
  ],
  "trades": [
    {
      "date": "2024-01-15",
      "action": "BUY",
      "quantity": 100,
      "price": 175.50,
      "symbol": "AAPL",
      "type": "stock"
    }
  ],
  "summary": {
    "total_trades": 15,
    "total_pnl": 2500.00,
    "win_rate": 73.3
  }
}
```

#### 3.3.3 AI 對話分析

**API 端點**:
```
POST /api/ai/chat
```

**請求格式**:
```json
{
  "symbol": "AAPL",
  "message": "分析我最近的交易",
  "session_id": "uuid-session-id"
}
```

**回應格式**:
```json
{
  "response": "根據你的 AAPL 交易記錄分析...",
  "session_id": "uuid-session-id"
}
```

#### 3.3.4 規則引擎偵測

自動偵測的交易模式：
- **追高 (Chasing High)**: 在近期高點買入
- **殺低 (Panic Selling)**: 在近期低點賣出
- **頻繁交易**: 短時間內多次買賣同一標的

### 3.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| REV-001 | 載入標的列表 | 顯示所有交易過的標的 |
| REV-002 | 顯示 K 線圖 | 正確渲染 OHLC 數據 |
| REV-003 | 標記買賣點 | 在 K 線圖上正確標記交易 |
| REV-004 | AI 對話 | 能夠進行多輪對話 |
| REV-005 | 規則偵測 | 正確識別追高行為 |

---

## 4. 交易日誌 (Trading Journal)

### 4.1 功能概述

提供 MFE/MAE 分析、交易計劃和日誌筆記功能。

### 4.2 前端路由

- **路徑**: `/journal`
- **子頁籤**: MFE/MAE、交易計劃、日誌筆記

### 4.3 MFE/MAE 分析

#### 4.3.1 定義

- **MFE (Maximum Favorable Excursion)**: 持有期間最大浮盈
- **MAE (Maximum Adverse Excursion)**: 持有期間最大浮虧
- **交易效率**: `實際盈虧 / MFE × 100%`

#### 4.3.2 API 端點

**取得統計摘要**:
```
GET /api/mfe-mae/stats
```

**回應格式**:
```json
{
  "avg_mfe": 5.2,
  "avg_mae": -2.8,
  "avg_efficiency": 68.5,
  "total_records": 150
}
```

**取得記錄列表**:
```
GET /api/mfe-mae/records?symbol=AAPL
```

**計算 MFE/MAE**:
```
POST /api/mfe-mae/calculate?symbol=AAPL&recalculate=true
```

**取得即時 Running MFE/MAE**:
```
GET /api/mfe-mae/running
```

#### 4.3.3 選擇權 MFE/MAE 特殊處理

- **計算方式**: 基於已實現盈虧而非標的價格移動
- **原因**: 選擇權價格受多重因素影響（Delta、Theta、IV）
- **效率計算**: 不適用於選擇權交易

### 4.4 交易計劃

#### 4.4.1 計劃欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | string | 標的代號 |
| direction | string | long / short |
| entry_trigger | string | 進場條件描述 |
| entry_price_min | float | 進場價格下限 |
| entry_price_max | float | 進場價格上限 |
| target_price | float | 目標價格 |
| stop_loss_price | float | 停損價格 |
| position_size | string | 部位大小描述 |
| max_risk_amount | float | 最大風險金額 |
| thesis | string | 交易論點 |
| valid_until | string | 有效期限 |

#### 4.4.2 API 端點

**取得計劃列表**:
```
GET /api/trade-plans?status=active&symbol=AAPL
```

**新增計劃**:
```
POST /api/trade-plans
```

**AI 生成計劃**:
```
POST /api/trade-plans/generate
```

**請求格式**:
```json
{
  "symbol": "AAPL",
  "direction": "long"
}
```

**AI 評價計劃**:
```
GET /api/trade-plans/{plan_id}/ai-review
```

**計劃事後分析**:
```
GET /api/trade-plans/{plan_id}/post-analysis
```

### 4.5 日誌筆記

#### 4.5.1 筆記類型

| 類型 | 說明 |
|------|------|
| daily | 每日交易日誌 |
| weekly | 每週檢討 |
| monthly | 每月總結 |
| trade | 單筆交易筆記 |
| misc | 其他觀察 |

#### 4.5.2 筆記欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| note_type | string | 筆記類型 |
| date | string | 日期 (YYYY-MM-DD) |
| symbol | string | 標的代號 (選填) |
| title | string | 標題 |
| content | string | 內容 |
| mood | string | 情緒狀態 |
| confidence_level | int | 信心水平 (1-5) |
| market_sentiment | string | 市場情緒 |
| key_observations | array | 關鍵觀察 |
| lessons_learned | string | 學到的教訓 |
| action_items | array | 行動項目 |
| tags | array | 標籤 |

#### 4.5.3 API 端點

**取得筆記列表**:
```
GET /api/trade-notes?note_type=daily&start_date=2024-01-01
```

**新增筆記**:
```
POST /api/trade-notes
```

**AI 生成筆記草稿**:
```
POST /api/trade-notes/generate
```

**AI 分析筆記**:
```
GET /api/trade-notes/{note_id}/ai-analysis
```

### 4.6 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| JRN-001 | MFE/MAE 計算 | 正確計算股票的 MFE/MAE |
| JRN-002 | 選擇權 MFE/MAE | 使用已實現盈虧計算 |
| JRN-003 | 創建交易計劃 | 成功儲存計劃 |
| JRN-004 | AI 生成計劃 | 生成合理的進出場建議 |
| JRN-005 | 日誌筆記 CRUD | 新增/讀取/更新/刪除正常 |
| JRN-006 | AI 生成筆記 | 根據當日交易生成草稿 |

---

## 5. 策略模擬 (Strategy Simulation)

### 5.1 功能概述

提供 What-if 情境分析，支援股票、選擇權和期貨。

### 5.2 前端路由

- **路徑**: `/strategy`

### 5.3 API 端點

**策略模擬**:
```
POST /api/strategy/simulate
```

**請求格式**:
```json
{
  "asset_type": "stock",
  "symbol": "AAPL",
  "quantity": 100,
  "avg_cost": 175.50,
  "current_price": 180.00,
  "iv": 0.25,
  "upcoming_events": "Q4 earnings on Jan 25",
  "goal": "profit_taking"
}
```

**回應格式**:
```json
{
  "recommendations": [
    {
      "strategy": "Covered Call",
      "description": "賣出 1 張 AAPL 185 Call",
      "risk_level": "Medium",
      "expected_return": "2.5% 月報酬"
    }
  ]
}
```

**AI 策略深度分析**:
```
POST /api/strategy/ai-advice
```

### 5.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| STR-001 | 股票策略模擬 | 返回合理策略建議 |
| STR-002 | 選擇權策略模擬 | 正確計算 Greeks |
| STR-003 | AI 策略分析 | 生成詳細分析報告 |

---

## 6. 績效報告 (Performance Report)

### 6.1 功能概述

提供完整的績效統計和 AI 評語。

### 6.2 前端路由

- **路徑**: `/report`

### 6.3 API 端點

**取得績效報告**:
```
GET /api/report/performance
```

**回應格式**:
```json
{
  "total_trades": 150,
  "wins": 98,
  "losses": 52,
  "win_rate": 65.3,
  "total_pnl": 25000.00,
  "avg_win": 450.50,
  "avg_loss": -220.25,
  "profit_factor": 2.15,
  "best_trade": 3500.00,
  "worst_trade": -1200.00,
  "pnl_by_symbol": {
    "AAPL": 8500.00,
    "GOOGL": 5200.00
  },
  "pnl_by_hour": {
    "9": 3500.00,
    "10": 2800.00,
    "15": -1500.00
  },
  "warnings": ["注意：下午 3 點的交易表現較差"]
}
```

**AI 績效評語**:
```
GET /api/report/ai-review
```

### 6.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| RPT-001 | 績效統計正確性 | 勝率計算準確 |
| RPT-002 | 時段分析 | 識別魔鬼時刻 |
| RPT-003 | AI 評語 | 生成有建設性的評論 |

---

## 7. 策略實驗室 (Strategy Lab)

### 7.1 功能概述

載入回測結果並進行分析。

### 7.2 前端路由

- **路徑**: `/lab`

### 7.3 API 端點

**列出回測結果**:
```
GET /api/lab/backtests
```

**取得回測結果**:
```
GET /api/lab/backtests/{filename}
```

### 7.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| LAB-001 | 列出回測 | 顯示可用的回測檔案 |
| LAB-002 | 載入回測 | 正確解析 JSON 結果 |

---

## 8. 選擇權顧問 (Options Advisor)

### 8.1 功能概述

根據市場看法推薦選擇權策略。

### 8.2 前端路由

- **路徑**: `/options`

### 8.3 API 端點

**取得選擇權建議**:
```
POST /api/options/advice
```

**請求格式**:
```json
{
  "symbol": "AAPL",
  "current_price": 180.00,
  "market_view": "bullish",
  "time_horizon": "1_month",
  "risk_tolerance": "moderate",
  "capital": 10000.00,
  "fifty_two_week_high": 200.00,
  "fifty_two_week_low": 140.00,
  "beta": 1.25
}
```

**回應格式**:
```json
{
  "recommended_strategy": "Bull Call Spread",
  "legs": [
    {"action": "buy", "strike": 180, "expiry": "2024-01-19", "type": "call"},
    {"action": "sell", "strike": 190, "expiry": "2024-01-19", "type": "call"}
  ],
  "max_profit": 800.00,
  "max_loss": 200.00,
  "breakeven": 182.00,
  "greeks": {
    "delta": 0.45,
    "gamma": 0.02,
    "theta": -5.50,
    "vega": 0.15
  }
}
```

### 8.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| OPT-001 | Bullish 策略 | 推薦看漲策略 |
| OPT-002 | Bearish 策略 | 推薦看跌策略 |
| OPT-003 | Neutral 策略 | 推薦 Iron Condor 等 |

---

## 9. Portfolio AI 顧問

### 9.1 功能概述

綜合分析投資組合，整合研究報告和市場數據。

### 9.2 前端路由

- **路徑**: `/ai`

### 9.3 API 端點

**AI 投資組合分析**:
```
POST /api/portfolio/ai-analysis
```

**請求格式**:
```json
{
  "include_reports": true
}
```

**AI 綜合審查**:
```
GET /api/ai/comprehensive-review
```

此 API 整合：
- MFE/MAE 分析結果
- 交易計劃
- 日誌筆記
- 當前持倉
- K 線圖數據

### 9.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| PAI-001 | 持倉分析 | 正確識別持倉風險 |
| PAI-002 | 整合報告 | 讀取 reports/ 目錄的 Markdown |
| PAI-003 | 綜合審查 | 生成完整審查報告 |

---

## 10. 錯誤卡片 (Mistake Cards)

### 10.1 功能概述

記錄交易失誤和教訓。

### 10.2 前端路由

- **路徑**: `/mistakes`

### 10.3 API 端點

**取得錯誤卡片**:
```
GET /api/mistakes
```

**新增錯誤卡片**:
```
POST /api/mistakes
```

**請求格式**:
```json
{
  "symbol": "AAPL",
  "date": "2024-01-15",
  "error_type": "追高",
  "description": "在高點追買...",
  "lesson": "等待回調再進場",
  "emotional_state": "FOMO"
}
```

### 10.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| MIS-001 | 新增卡片 | 成功儲存 |
| MIS-002 | 列出卡片 | 按日期排序顯示 |

---

## 11. 設定 (Settings)

### 11.1 功能概述

管理系統設定、API Keys 和通知。

### 11.2 前端路由

- **路徑**: `/settings`

### 11.3 API 端點

**取得設定**:
```
GET /api/settings
```

**更新設定**:
```
POST /api/settings
```

**取得設定狀態**:
```
GET /api/config/status
```

**回應格式**:
```json
{
  "ibkr": {
    "configured": true,
    "flex_token": "***已設定***",
    "history_query_id": "1234567",
    "positions_query_id": "7654321"
  },
  "ai": {
    "configured": true,
    "provider": "gemini",
    "gemini_key": "***已設定***"
  },
  "telegram": {
    "configured": true,
    "bot_token": "***已設定***",
    "chat_id": "12345678",
    "daily_time": "08:00"
  }
}
```

**驗證設定**:
```
POST /api/config/validate
```

**儲存設定**:
```
POST /api/config/save
```

### 11.4 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| SET-001 | 讀取設定 | 返回當前設定 |
| SET-002 | 驗證 IBKR | 成功連接 IBKR API |
| SET-003 | 驗證 Gemini | API Key 有效 |
| SET-004 | 儲存設定 | 設定立即生效 |

---

## 12. IBKR 整合

### 12.1 功能概述

透過 Flex Query API 自動同步交易記錄和持倉。

### 12.2 資料來源分工（重要）

| 資料項目 | 來源 | 說明 |
|----------|------|------|
| 交易記錄 | **IBKR** | Symbol、日期、數量、價格、手續費 |
| 持倉數量 | **IBKR** | 股數/合約數、方向 |
| 成本基礎 | **IBKR** | 平均成本 |
| 現金餘額 | **IBKR** | 總現金、已結算現金 |
| 選擇權詳情 | **IBKR** | Strike、Expiry、Put/Call |
| **股票即時價格** | **Yahoo Finance** | 每 60 秒自動更新 |

> ⚠️ **注意**: IBKR **不負責** 提供即時股票價格。所有股票價格由 Yahoo Finance (yfinance) 提供。

### 12.3 必要設定

| 環境變數 | 說明 |
|----------|------|
| IBKR_FLEX_TOKEN | Flex Query Token |
| IBKR_HISTORY_QUERY_ID | 交易歷史 Query ID |
| IBKR_POSITIONS_QUERY_ID | 持倉快照 Query ID |

### 12.3 API 端點

**同步 IBKR 數據**:
```
POST /api/ibkr/sync
```

**回應格式**:
```json
{
  "success": true,
  "trades_synced": 25,
  "positions_synced": 8,
  "message": "同步完成"
}
```

**取得現金餘額**:
```
GET /api/ibkr/cash
```

**回應格式**:
```json
{
  "total_cash": 50000.00,
  "currency": "USD",
  "ending_cash": 50000.00,
  "ending_settled_cash": 48500.00
}
```

### 12.4 安全解析功能

為防止 IBKR 返回的異常值導致錯誤，實作了以下安全函數：

- `safe_float(value, default, allow_negative)`: 安全轉換浮點數
- `safe_int(value, default, allow_negative)`: 安全轉換整數
- `safe_date_parse(date_str, formats)`: 安全解析日期

### 12.5 支援的日期格式

- YYYYMMDD
- YYYY-MM-DD
- YYYYMMDD;HHMMSS
- YYYY/MM/DD

### 12.6 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| IBKR-001 | 同步交易 | 成功匯入新交易 |
| IBKR-002 | 同步持倉 | 更新持倉快照 |
| IBKR-003 | 空值處理 | 不因空值而失敗 |
| IBKR-004 | 日期解析 | 正確解析各種格式 |

---

## 13. AI 功能

### 13.1 支援的 AI 服務商

| 服務商 | 模型 | 用途 |
|--------|------|------|
| Google Gemini | gemini-1.5-pro | 預設 AI 引擎 |
| DeepSeek | deepseek-chat | 備選方案 |
| OpenAI | gpt-4 | 備選方案 |

### 13.2 AI 功能列表

| 功能 | API 端點 | 說明 |
|------|----------|------|
| 對話分析 | POST /api/ai/chat | 交易對話式分析 |
| 績效評語 | GET /api/report/ai-review | AI 績效評論 |
| 策略建議 | POST /api/strategy/ai-advice | AI 策略分析 |
| 選擇權建議 | POST /api/options/advice | AI 選擇權策略 |
| 投資組合分析 | POST /api/portfolio/ai-analysis | AI 風險評估 |
| 綜合審查 | GET /api/ai/comprehensive-review | 全面分析 |
| 計劃評價 | GET /api/trade-plans/{id}/ai-review | 計劃可行性 |
| 筆記分析 | GET /api/trade-notes/{id}/ai-analysis | 筆記建議 |
| 生成筆記 | POST /api/trade-notes/generate | AI 草稿 |
| 生成計劃 | POST /api/trade-plans/generate | AI 計劃 |

### 13.3 測試用例

| 測試 ID | 測試名稱 | 預期結果 |
|---------|----------|----------|
| AI-001 | Gemini 連線 | API 驗證成功 |
| AI-002 | 對話上下文 | 保持多輪對話 |
| AI-003 | 回應格式 | Markdown 格式正確 |

---

## 14. API 端點完整清單

### 14.1 交易相關

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/trades | 取得交易記錄 |
| GET | /api/trades/symbols | 取得所有標的 |
| GET | /api/trades/pnl-by-symbol | 標的盈虧統計 |

### 14.2 統計相關

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/statistics | 交易統計 |
| GET | /api/equity-curve | 資金曲線 |

### 14.3 持倉相關

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/portfolio | 持倉總覽 |
| POST | /api/ibkr/sync | 同步 IBKR |
| GET | /api/ibkr/cash | 現金餘額 |

### 14.4 AI 相關

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | /api/ai/chat | AI 對話 |
| POST | /api/ai/analyze-portfolio | 分析投資組合 |
| GET | /api/ai/comprehensive-review | 綜合審查 |

### 14.5 績效報告

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/report/performance | 績效報告 |
| GET | /api/report/ai-review | AI 評語 |

### 14.6 策略模擬

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | /api/strategy/simulate | 策略模擬 |
| POST | /api/strategy/ai-advice | AI 策略建議 |

### 14.7 選擇權

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | /api/options/advice | 選擇權建議 |

### 14.8 MFE/MAE

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/mfe-mae/stats | 統計摘要 |
| GET | /api/mfe-mae/records | 記錄列表 |
| POST | /api/mfe-mae/calculate | 計算 MFE/MAE |
| GET | /api/mfe-mae/running | 即時 MFE/MAE |
| GET | /api/mfe-mae/ai-advice | AI 建議 |

### 14.9 交易計劃

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/trade-plans | 計劃列表 |
| POST | /api/trade-plans | 新增計劃 |
| GET | /api/trade-plans/{id} | 單一計劃 |
| PUT | /api/trade-plans/{id} | 更新計劃 |
| DELETE | /api/trade-plans/{id} | 刪除計劃 |
| POST | /api/trade-plans/generate | AI 生成 |
| GET | /api/trade-plans/{id}/ai-review | AI 評價 |
| GET | /api/trade-plans/{id}/post-analysis | 事後分析 |

### 14.10 日誌筆記

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/trade-notes | 筆記列表 |
| POST | /api/trade-notes | 新增筆記 |
| GET | /api/trade-notes/{id} | 單一筆記 |
| PUT | /api/trade-notes/{id} | 更新筆記 |
| DELETE | /api/trade-notes/{id} | 刪除筆記 |
| POST | /api/trade-notes/generate | AI 生成 |
| GET | /api/trade-notes/{id}/ai-analysis | AI 分析 |

### 14.11 錯誤卡片

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/mistakes | 卡片列表 |
| POST | /api/mistakes | 新增卡片 |

### 14.12 市場數據

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/market/quote/{symbol} | 即時報價 |
| GET | /api/market/history/{symbol} | 歷史價格 |

### 14.13 交易檢討

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/review/chart/{underlying} | K 線圖數據 |
| GET | /api/review/grouped-symbols | 分組標的 |

### 14.14 設定

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | /api/settings | 取得設定 |
| POST | /api/settings | 更新設定 |
| GET | /api/config/status | 設定狀態 |
| POST | /api/config/validate | 驗證設定 |
| POST | /api/config/save | 儲存設定 |

### 14.15 資料庫維護

| 方法 | 端點 | 說明 |
|------|------|------|
| POST | /api/db/recalculate-pnl | 重算盈虧 |
| POST | /api/db/clear | 清空資料庫 |

---

## 15. 資料庫結構

### 15.1 主要資料表

| 資料表 | 說明 |
|--------|------|
| trades | 交易記錄 |
| trade_plans | 交易計劃 |
| trade_notes | 日誌筆記 |
| open_positions | 持倉快照 |
| cash_snapshots | 現金快照 |
| mfe_mae_records | MFE/MAE 記錄 |
| mistake_cards | 錯誤卡片 |
| chat_history | AI 對話歷史 |
| settings | 系統設定 |

### 15.2 trades 資料表結構

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | TEXT (PK) | 交易 ID (hash) |
| datetime | TEXT | 交易時間 |
| symbol | TEXT | 標的代號 |
| action | TEXT | BUY/SELL |
| quantity | REAL | 數量 |
| price | REAL | 價格 |
| commission | REAL | 手續費 |
| realized_pnl | REAL | 已實現盈虧 |
| instrument_type | TEXT | stock/option |
| strike | REAL | 履約價 (選擇權) |
| expiry | TEXT | 到期日 (選擇權) |
| option_type | TEXT | Call/Put (選擇權) |
| underlying | TEXT | 標的股票 |

---

## 16. 測試用例

### 16.1 完整測試清單

| 測試 ID | 類別 | 說明 | 優先級 |
|---------|------|------|--------|
| DASH-001 | 儀表板 | 載入 KPI | High |
| DASH-002 | 儀表板 | 日期篩選 | High |
| DASH-003 | 儀表板 | 持倉顯示 | High |
| DASH-004 | 儀表板 | 策略識別 | Medium |
| DASH-005 | 儀表板 | 價格自動更新 | Medium |
| DASH-006 | 儀表板 | 現金餘額 | High |
| REV-001 | 交易檢討 | 標的列表 | High |
| REV-002 | 交易檢討 | K 線圖 | Medium |
| REV-003 | 交易檢討 | 買賣點標記 | Medium |
| REV-004 | 交易檢討 | AI 對話 | High |
| JRN-001 | 日誌 | MFE/MAE 計算 | High |
| JRN-002 | 日誌 | 選擇權 MFE/MAE | High |
| JRN-003 | 日誌 | 創建計劃 | High |
| JRN-004 | 日誌 | AI 生成計劃 | Medium |
| JRN-005 | 日誌 | 筆記 CRUD | High |
| IBKR-001 | 整合 | 同步交易 | High |
| IBKR-002 | 整合 | 同步持倉 | High |
| IBKR-003 | 整合 | 空值處理 | High |
| IBKR-004 | 整合 | 日期解析 | High |
| AI-001 | AI | API 連線 | High |
| AI-002 | AI | 對話上下文 | Medium |

### 16.2 端對端測試流程

1. **環境準備**
   - 啟動後端 (port 8000)
   - 啟動前端 (port 3000)
   - 設定 API Keys

2. **IBKR 同步測試**
   - 呼叫 POST /api/ibkr/sync
   - 驗證 trades 和 positions 已匯入

3. **儀表板測試**
   - 訪問 http://localhost:3000
   - 驗證 KPI 顯示正確數值
   - 選擇不同日期範圍

4. **AI 功能測試**
   - 進行 AI 對話
   - 取得績效評語
   - 生成交易計劃

5. **MFE/MAE 測試**
   - 計算 MFE/MAE
   - 驗證股票和選擇權分別處理

---

## 附錄

### A. 環境變數

```bash
# AI API Keys
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENAI_API_KEY=your_openai_key

# IBKR Flex Query
IBKR_FLEX_TOKEN=your_ibkr_token
IBKR_HISTORY_QUERY_ID=your_history_query_id
IBKR_POSITIONS_QUERY_ID=your_positions_query_id

# Telegram (可選)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### B. 快速啟動

```bash
# 安裝依賴
uv sync
cd frontend && npm install

# 啟動
./run-dev.sh
```

### C. API 文檔

訪問 http://localhost:8000/docs 查看自動生成的 OpenAPI 文檔。

---

**文件結束**
