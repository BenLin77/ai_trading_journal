# IBKR Flex Query 設定指南

> **版本**: 2.1.0  
> **最後更新**: 2024-12-16

## 概述

本系統透過 IBKR Flex Query API 自動同步交易記錄和庫存快照，無需手動匯出 CSV。

## ⚠️ 重要：資料來源分工

| 資料項目 | 來源 | 說明 |
|----------|------|------|
| 交易記錄 | **IBKR** | Symbol、日期、數量、價格、手續費 |
| 持倉數量 | **IBKR** | 股數/合約數、方向 |
| 成本基礎 | **IBKR** | 平均成本 |
| 現金餘額 | **IBKR** | 總現金、已結算現金 |
| 選擇權詳情 | **IBKR** | Strike、Expiry、Put/Call |
| **股票即時價格** | **Yahoo Finance** | 每 60 秒自動更新 |

> ⚠️ **注意**: IBKR **不負責** 提供即時股票價格。所有股票價格由 Yahoo Finance (yfinance) 提供。

---

## 設定步驟

### 1. 登入 IBKR Client Portal

前往：https://www.interactivebrokers.com/portal

### 2. 生成 Flex Web Service Token

1. 點選 **Settings** → **Account Settings**
2. 找到 **Reporting** 區塊 → **Flex Web Service**
3. 點擊 **Generate Token**
4. 複製並保存 Token（僅顯示一次）

---

### 3. 建立 Flex Query - 交易歷史（History Query）

1. 前往 **Reports** → **Flex Queries** → **Activity Flex Query**
2. 點擊 **Create** 建立新查詢
3. 設定以下內容：

#### 基本設定
| 設定項目 | 建議值 |
|----------|--------|
| **Name** | Trading History |
| **Date Format** | yyyy-MM-dd |
| **Time Format** | HH:mm:ss |
| **Period** | Last 365 days（建議）或自訂範圍 |
| **Format** | XML 或 CSV（皆可） |

#### ✅ 必須勾選的區段（Sections）

##### 📋 Trades（交易記錄）- **必須**

| 欄位名稱 | 是否必須 | 說明 |
|----------|----------|------|
| Symbol | ✅ 必須 | 標的代號 |
| DateTime | ✅ 必須 | 交易時間 |
| TradeDate | ✅ 必須 | 交易日期 |
| Quantity | ✅ 必須 | 數量 |
| TradePrice | ✅ 必須 | 成交價格 |
| Proceeds | ✅ 必須 | 成交金額 |
| IBCommission | ✅ 必須 | 手續費 |
| IBCommissionCurrency | ⭕ 建議 | 手續費幣別 |
| NetCash | ⭕ 建議 | 淨現金流 |
| Buy/Sell | ✅ 必須 | 買賣方向 |
| AssetCategory | ✅ 必須 | 資產類別（STK/OPT） |
| Description | ⭕ 建議 | 標的描述 |
| Put/Call | ✅ 選擇權必須 | Call 或 Put |
| Strike | ✅ 選擇權必須 | 履約價 |
| Expiry | ✅ 選擇權必須 | 到期日 |
| Multiplier | ✅ 選擇權必須 | 合約乘數 |
| UnderlyingSymbol | ⭕ 建議 | 標的股票代號 |
| FifoPnlRealized | ⭕ 建議 | 已實現盈虧 |
| Open/CloseIndicator | ⭕ 建議 | 開平倉標記 |

##### 💰 Cash Report（現金報告）- **必須**

| 欄位名稱 | 是否必須 | 說明 |
|----------|----------|------|
| StartingCash | ⭕ 建議 | 期初現金 |
| EndingCash | ✅ 必須 | 期末現金 |
| EndingSettledCash | ✅ 必須 | 期末已結算現金 |
| CurrencyPrimary | ⭕ 建議 | 幣別 |

4. 點擊 **Save**
5. 記下 **Query ID**（右上角顯示）→ 這是 `IBKR_HISTORY_QUERY_ID`

---

### 4. 建立 Flex Query - 持倉快照（Positions Query）

1. 再次點擊 **Create** 建立新查詢

#### 基本設定
| 設定項目 | 建議值 |
|----------|--------|
| **Name** | Current Positions |
| **Date Format** | yyyy-MM-dd |
| **Period** | Today（當日） |
| **Format** | XML 或 CSV（皆可） |

#### ✅ 必須勾選的區段（Sections）

##### 📦 Open Positions（持倉）- **必須**

| 欄位名稱 | 是否必須 | 說明 |
|----------|----------|------|
| Symbol | ✅ 必須 | 標的代號 |
| Position | ✅ 必須 | 持倉數量 |
| MarkPrice | ✅ 必須 | 市價 |
| CostBasisPrice | ✅ 必須 | 平均成本 |
| FifoPnlUnrealized | ✅ 必須 | 未實現盈虧 |
| AssetCategory | ✅ 必須 | 資產類別 |
| Description | ⭕ 建議 | 標的描述 |
| Put/Call | ✅ 選擇權必須 | Call 或 Put |
| Strike | ✅ 選擇權必須 | 履約價 |
| Expiry | ✅ 選擇權必須 | 到期日 |
| Multiplier | ✅ 選擇權必須 | 合約乘數 |

3. 點擊 **Save**
4. 記下 **Query ID** → 這是 `IBKR_POSITIONS_QUERY_ID`

---

### 5. 設定環境變數

編輯專案根目錄的 `.env` 檔案：

```bash
# IBKR Flex Query 設定
IBKR_FLEX_TOKEN=your_actual_token_here
IBKR_HISTORY_QUERY_ID=1234567     # 交易歷史 Query ID
IBKR_POSITIONS_QUERY_ID=7654321   # 持倉快照 Query ID
```

---

## 常見問題診斷

### ❌ 現金餘額顯示 $0.00

**原因**: Flex Query 沒有勾選 **Cash Report** 區段

**解決方法**:
1. 編輯你的 History Query
2. 在 Sections 中找到 **Cash Report**
3. 勾選 **EndingCash** 和 **EndingSettledCash**
4. 儲存並重新同步

### ❌ 交易記錄沒有更新（股數不對）

**原因**: Flex Query 沒有勾選 **Trades** 區段

**解決方法**:
1. 編輯你的 History Query
2. 確保 Sections 中有勾選 **Trades**
3. 確保勾選了所有必須欄位
4. 確認 Period 設定涵蓋你的交易日期
5. 儲存並重新同步

### ❌ Error 1019: Statement generation in progress

**原因**: 報表正在生成中

**解決方法**: 系統已自動重試（最多 5 次，每次間隔 10 秒）。如果仍然失敗，請稍後再試。

### ❌ CSV 解析失敗

**原因**: Flex Query 返回了多種格式混合的報表

**解決方法**: 確保只勾選需要的區段，避免過多欄位衝突。

---

## API 限制與注意事項

### 請求限制
- Flex Query API 無明確的速率限制
- 建議每次請求間隔至少 1 秒
- 生成報表可能需要 5-30 秒（系統自動等待）

### 數據延遲
- 交易記錄：T+0（當日收盤後可用）
- 庫存快照：即時（當下狀態）
- 建議每日收盤後執行同步

### 錯誤處理
系統已實作自動重試和錯誤記錄：
- Error 1019（報表生成中）→ 自動重試 5 次
- XML/CSV 解析失敗 → 記錄到 log
- 網路連線失敗 → 拋出 Exception
- Token 錯誤 → 顯示設定提示

---

## 使用方式

### 透過 Web UI 同步

1. 啟動系統
2. 點擊右上角的 **Sync** 按鈕
3. 系統會自動：
   - 取得交易記錄
   - 取得庫存快照
   - 匯入資料庫
   - 更新現金餘額

### 透過 API 同步

```bash
curl -X POST http://localhost:8000/api/ibkr/sync
```

### 透過程式碼調用

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

---

## Query ID 速查表

| 環境變數 | 用途 | 必須勾選的區段 |
|----------|------|---------------|
| `IBKR_HISTORY_QUERY_ID` | 交易歷史 | Trades, Cash Report |
| `IBKR_POSITIONS_QUERY_ID` | 持倉快照 | Open Positions |

---

## 安全建議

1. **保護 Token**：.env 檔案已加入 .gitignore，嚴禁提交到 Git
2. **唯讀權限**：Flex Query API 為唯讀，無法執行交易
3. **定期檢查**：每月檢查一次 Token 使用紀錄（Client Portal 可查看）

---

## 技術文件

- [IBKR Flex Web Service API v3](https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm)
- [Flex Query 欄位說明](https://www.interactivebrokers.com/en/software/am/am/reports/activityflexqueries.htm)

## 相關檔案

- [`utils/ibkr_flex_query.py`](../utils/ibkr_flex_query.py): Flex Query API 客戶端
- [`database.py`](../database.py): 資料庫操作
- [`backend/main.py`](../backend/main.py): API 端點

