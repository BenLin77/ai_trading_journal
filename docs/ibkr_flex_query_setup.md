# IBKR Flex Query 設定指南

## 概述

本系統透過 IBKR Flex Query API 自動同步交易記錄和庫存快照，無需手動匯出 CSV。

## 架構說明

### 數據流
```
IBKR Account
    ↓ (Flex Query API)
utils/ibkr_flex_query.py
    ↓ (自動同步)
database.py (trades + open_positions 表)
    ↓ (使用)
Portfolio Advisor / 其他分析頁面
```

### 數據來源分工
- **交易記錄 & 庫存快照**: IBKR Flex Query（透過 Token 和 Query ID）
- **選擇權市場數據**: yfinance（IV、Volume、OI、Put/Call Ratio）

## 設定步驟

### 1. 登入 IBKR Client Portal
前往：https://www.interactivebrokers.com/portal

### 2. 生成 Flex Web Service Token

1. 點選 **Settings** → **Account Settings**
2. 找到 **Flex Web Service** 區塊
3. 點擊 **Generate Token**
4. 複製並保存 Token（僅顯示一次）

### 3. 建立 Flex Query - 交易記錄

1. 前往 **Reports** → **Flex Queries** → **Activity Flex Query**
2. 點擊 **Create** 建立新查詢
3. 設定以下欄位：

#### 基本設定
- **Name**: Daily Trades
- **Date Format**: yyyy-MM-dd
- **Time Format**: HH:mm:ss
- **Period**: Last Trading Day（前一日交易）

#### 選擇欄位（Sections）
勾選 **Trades**，並選擇以下欄位：
- ✅ Symbol
- ✅ Date/Time
- ✅ Quantity
- ✅ Price (Trade Price)
- ✅ Proceeds
- ✅ Comm/Fee
- ✅ Net Cash
- ✅ Asset Category
- ✅ Description
- ✅ Put/Call（選擇權）
- ✅ Strike（選擇權）
- ✅ Expiry（選擇權）
- ✅ Multiplier（選擇權）

4. 點擊 **Save**
5. 記下 **Query ID**（右上角顯示）

### 4. 建立 Flex Query - 庫存快照

1. 再次點擊 **Create** 建立新查詢
2. 設定以下欄位：

#### 基本設定
- **Name**: Current Positions
- **Date Format**: yyyy-MM-dd
- **Period**: Today（當日）

#### 選擇欄位（Sections）
勾選 **Open Positions**，並選擇以下欄位：
- ✅ Symbol
- ✅ Position
- ✅ Mark Price
- ✅ Cost Basis Price (Average Cost)
- ✅ FIFO P/L Unrealized (Unrealized P/L)
- ✅ Asset Category
- ✅ Description
- ✅ Put/Call（選擇權）
- ✅ Strike（選擇權）
- ✅ Expiry（選擇權）
- ✅ Multiplier（選擇權）

3. 點擊 **Save**
4. 記下 **Query ID**

### 5. 設定環境變數

編輯專案根目錄的 `.env` 檔案：

```bash
# IBKR Flex Query 設定
IBKR_FLEX_TOKEN=your_actual_token_here
IBKR_TRADES_QUERY_ID=123456  # 交易記錄 Query ID
IBKR_POSITIONS_QUERY_ID=123457  # 庫存快照 Query ID
```

### 6. 測試連接

執行測試腳本：

```bash
uv run python -c "from utils.ibkr_flex_query import IBKRFlexQuery; flex = IBKRFlexQuery(); print('✅ 連接成功')"
```

## 使用方式

### 方法 1：透過 UI 手動同步

1. 啟動系統：`uv run streamlit run Home.py`
2. 在首頁點擊 **📥 執行同步** 按鈕
3. 系統會自動：
   - 取得前一日交易記錄
   - 取得當前庫存快照
   - 匯入資料庫
   - 重新計算損益（FIFO）

### 方法 2：透過程式碼調用

```python
from utils.ibkr_flex_query import IBKRFlexQuery
from database import TradingDatabase

# 初始化
flex = IBKRFlexQuery()
db = TradingDatabase()

# 同步數據
result = flex.sync_to_database(db)
print(f"交易記錄：{result['trades']} 筆")
print(f"庫存快照：{result['positions']} 個部位")
```

### 方法 3：設定自動排程（推薦）

使用 cron（macOS/Linux）或 Task Scheduler（Windows）：

```bash
# 每天早上 9:00 自動同步
0 9 * * * cd /path/to/ai_trading_journal && /path/to/uv run python -c "from utils.ibkr_flex_query import IBKRFlexQuery; from database import TradingDatabase; flex = IBKRFlexQuery(); db = TradingDatabase(); flex.sync_to_database(db)"
```

## API 限制與注意事項

### 請求限制
- Flex Query API 無明確的速率限制
- 建議每次請求間隔至少 1 秒
- 生成報表可能需要 2-10 秒

### 數據延遲
- 交易記錄：T+0（當日收盤後可用）
- 庫存快照：即時（當下狀態）
- 建議每日收盤後執行同步

### 錯誤處理
系統已實作自動重試和錯誤記錄：
- XML 解析失敗 → 記錄到 log
- 網路連線失敗 → 拋出 Exception
- Token 錯誤 → 顯示設定提示

## 常見問題

### Q1: Token 過期怎麼辦？
IBKR Flex Token 無過期時間，但可以隨時 Revoke。若需更新：
1. 登入 Client Portal
2. Revoke 舊 Token
3. Generate 新 Token
4. 更新 `.env` 檔案

### Q2: Query ID 在哪裡查看？
1. 登入 Client Portal
2. Reports → Flex Queries
3. 點選已建立的 Query
4. 右上角會顯示 Query ID

### Q3: 如何驗證數據正確性？
```bash
# 檢查最新庫存
uv run python -c "from database import TradingDatabase; db = TradingDatabase(); import pandas as pd; print(pd.DataFrame(db.get_latest_positions()))"

# 檢查最新交易
uv run python -c "from database import TradingDatabase; db = TradingDatabase(); print(db.get_recent_trades(limit=10))"
```

### Q4: 選擇權數據格式如何識別？
系統會自動解析 IBKR 回傳的選擇權數據：
- `putCall`: C = Call, P = Put
- `strike`: 履約價
- `expiry`: 到期日（YYYYMMDD）
- `multiplier`: 合約乘數（通常為 100）

## 安全建議

1. **保護 Token**：.env 檔案已加入 .gitignore，嚴禁提交到 Git
2. **唯讀權限**：Flex Query API 為唯讀，無法執行交易
3. **定期檢查**：每月檢查一次 Token 使用紀錄（Client Portal 可查看）

## 技術文件

- [IBKR Flex Web Service API v3](https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm)
- [Flex Query 欄位說明](https://www.interactivebrokers.com/en/software/am/am/reports/activityflexqueries.htm)

## 相關檔案

- [`utils/ibkr_flex_query.py`](../utils/ibkr_flex_query.py): Flex Query API 客戶端
- [`database.py`](../database.py): 資料庫操作（含 open_positions 表）
- [`Home.py`](../Home.py): UI 同步按鈕
- [`.env.example`](../.env.example): 環境變數範本
