# AI Trading Journal - 測試指南

> **版本**: 2.0.0  
> **最後更新**: 2024-12-16  
> **文件目的**: 提供詳細的測試步驟，可供 AI 自動化測試工具執行

---

## 目錄

1. [測試環境設置](#1-測試環境設置)
2. [API 測試用例](#2-api-測試用例)
3. [前端測試用例](#3-前端測試用例)
4. [整合測試用例](#4-整合測試用例)
5. [錯誤處理測試](#5-錯誤處理測試)
6. [效能測試](#6-效能測試)

---

## 1. 測試環境設置

### 1.1 前置條件

```bash
# 確認 Python 版本
python --version  # 應為 3.10+

# 確認 Node.js 版本
node --version  # 應為 20+

# 安裝依賴
cd /path/to/ai_trading_journal
uv sync
cd frontend && npm install
```

### 1.2 啟動測試環境

```bash
# 方式一：使用開發腳本
./run-dev.sh

# 方式二：分別啟動
# 終端 1 - 後端
cd backend && uv run uvicorn main:app --reload --port 8000

# 終端 2 - 前端
cd frontend && npm run dev
```

### 1.3 測試資料準備

```bash
# 匯入測試資料（如果需要）
curl -X POST http://localhost:8000/api/ibkr/sync
```

---

## 2. API 測試用例

### 2.1 健康檢查

**測試 ID**: API-HEALTH-001

```bash
curl http://localhost:8000/health
```

**預期回應**:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai": "available"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] status = "healthy"
- [ ] database = "connected"

---

### 2.2 交易統計

**測試 ID**: API-STATS-001

```bash
curl "http://localhost:8000/api/statistics"
```

**預期回應格式**:
```json
{
  "total_trades": "<integer>",
  "total_pnl": "<float>",
  "win_rate": "<float, 0-100>",
  "avg_win": "<float>",
  "avg_loss": "<float>",
  "profit_factor": "<float>",
  "best_trade": "<float>",
  "worst_trade": "<float>"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] total_trades >= 0
- [ ] win_rate 在 0-100 之間
- [ ] profit_factor >= 0

---

**測試 ID**: API-STATS-002 (帶日期篩選)

```bash
curl "http://localhost:8000/api/statistics?start_date=2024-01-01&end_date=2024-12-31"
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回的統計數據僅包含指定日期範圍

---

### 2.3 持倉總覽

**測試 ID**: API-PORTFOLIO-001

```bash
curl "http://localhost:8000/api/portfolio"
```

**預期回應格式**:
```json
{
  "positions": [
    {
      "symbol": "<string>",
      "underlying": "<string>",
      "quantity": "<float>",
      "avg_cost": "<float>",
      "current_price": "<float | null>",
      "market_value": "<float | null>",
      "unrealized_pnl": "<float | null>",
      "unrealized_pnl_pct": "<float | null>",
      "strategy": "<string | null>",
      "strategy_description": "<string | null>",
      "risk_level": "<string | null>",
      "options": [...]
    }
  ],
  "total_market_value": "<float>",
  "total_unrealized_pnl": "<float>",
  "total_realized_pnl": "<float>",
  "cash_balance": "<float>"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] positions 是陣列
- [ ] 每個 position 有必要欄位
- [ ] total_market_value 是所有 position market_value 的總和

---

### 2.4 現金餘額

**測試 ID**: API-CASH-001

```bash
curl "http://localhost:8000/api/ibkr/cash"
```

**預期回應格式**:
```json
{
  "total_cash": "<float>",
  "currency": "USD",
  "ending_cash": "<float>",
  "ending_settled_cash": "<float>"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200 或 404
- [ ] 如果 200，total_cash 是數值
- [ ] 如果 404，應返回提示訊息

---

### 2.5 AI 對話

**測試 ID**: API-AI-CHAT-001

```bash
curl -X POST "http://localhost:8000/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "分析我的持倉風險", "session_id": "test-session-001"}'
```

**預期回應格式**:
```json
{
  "response": "<string, AI 生成的回應>",
  "session_id": "test-session-001"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] response 是非空字串
- [ ] session_id 與請求相符

---

**測試 ID**: API-AI-CHAT-002 (多輪對話)

```bash
# 第一輪
curl -X POST "http://localhost:8000/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "我持有 100 股 AAPL", "session_id": "test-multi-001"}'

# 第二輪（應該記得上下文）
curl -X POST "http://localhost:8000/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "它的風險如何", "session_id": "test-multi-001"}'
```

**驗證點**:
- [ ] 第二輪回應提及 AAPL（表示記得上下文）

---

### 2.6 MFE/MAE

**測試 ID**: API-MFEMAE-001

```bash
curl "http://localhost:8000/api/mfe-mae/stats"
```

**預期回應格式**:
```json
{
  "avg_mfe": "<float | null>",
  "avg_mae": "<float | null>",
  "avg_efficiency": "<float | null>",
  "total_records": "<integer>"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] total_records >= 0

---

**測試 ID**: API-MFEMAE-002 (計算)

```bash
curl -X POST "http://localhost:8000/api/mfe-mae/calculate?recalculate=true"
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回計算的記錄數

---

### 2.7 交易計劃

**測試 ID**: API-PLAN-001 (新增)

```bash
curl -X POST "http://localhost:8000/api/trade-plans" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "direction": "long",
    "entry_price_min": 175.00,
    "entry_price_max": 180.00,
    "target_price": 200.00,
    "stop_loss_price": 170.00,
    "thesis": "看好 Q1 業績"
  }'
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回新建計劃的 ID

---

**測試 ID**: API-PLAN-002 (讀取)

```bash
curl "http://localhost:8000/api/trade-plans?status=active"
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回計劃列表

---

**測試 ID**: API-PLAN-003 (AI 生成)

```bash
curl -X POST "http://localhost:8000/api/trade-plans/generate" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "direction": "long"}'
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回包含 entry/target/stop_loss 的計劃

---

### 2.8 日誌筆記

**測試 ID**: API-NOTE-001 (新增)

```bash
curl -X POST "http://localhost:8000/api/trade-notes" \
  -H "Content-Type: application/json" \
  -d '{
    "note_type": "daily",
    "date": "2024-12-16",
    "title": "每日交易日誌",
    "content": "今天市場上漲，持倉表現良好",
    "mood": "positive",
    "confidence_level": 4
  }'
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回新建筆記的 ID

---

**測試 ID**: API-NOTE-002 (AI 生成)

```bash
curl -X POST "http://localhost:8000/api/trade-notes/generate" \
  -H "Content-Type: application/json" \
  -d '{"note_type": "daily", "date": "2024-12-16"}'
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回包含 title 和 content 的草稿

---

### 2.9 IBKR 同步

**測試 ID**: API-IBKR-001

```bash
curl -X POST "http://localhost:8000/api/ibkr/sync"
```

**預期回應格式**:
```json
{
  "success": "<boolean>",
  "trades_synced": "<integer>",
  "positions_synced": "<integer>",
  "message": "<string>"
}
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] success = true 或有明確錯誤訊息

---

### 2.10 設定

**測試 ID**: API-CONFIG-001 (狀態)

```bash
curl "http://localhost:8000/api/config/status"
```

**驗證點**:
- [ ] HTTP 狀態碼 = 200
- [ ] 返回 ibkr、ai、telegram 的設定狀態

---

**測試 ID**: API-CONFIG-002 (驗證 IBKR)

```bash
curl -X POST "http://localhost:8000/api/config/validate" \
  -H "Content-Type: application/json" \
  -d '{"config_type": "ibkr", "token": "your_token", "query_id": "123456"}'
```

**驗證點**:
- [ ] 返回驗證結果（成功或失敗原因）

---

## 3. 前端測試用例

### 3.1 頁面載入

**測試 ID**: FE-LOAD-001 (儀表板)

1. 訪問 http://localhost:3000
2. 等待頁面載入完成

**驗證點**:
- [ ] 頁面無 JavaScript 錯誤
- [ ] KPI 卡片顯示數值
- [ ] 資金曲線圖正常渲染
- [ ] 持倉列表顯示

---

**測試 ID**: FE-LOAD-002 (交易檢討)

1. 訪問 http://localhost:3000/review

**驗證點**:
- [ ] 標的選擇器載入
- [ ] 選擇標的後 K 線圖顯示

---

**測試 ID**: FE-LOAD-003 (日誌)

1. 訪問 http://localhost:3000/journal

**驗證點**:
- [ ] 頁籤切換正常（MFE/MAE、計劃、筆記）
- [ ] 列表正常顯示

---

### 3.2 互動測試

**測試 ID**: FE-INTERACT-001 (日期選擇)

1. 在儀表板點擊「1M」快捷按鈕
2. 觀察統計數據變化

**驗證點**:
- [ ] KPI 數值更新
- [ ] 資金曲線更新

---

**測試 ID**: FE-INTERACT-002 (AI 對話)

1. 前往交易檢討頁面
2. 選擇一個標的
3. 在對話框輸入「分析這個標的的交易」
4. 發送訊息

**驗證點**:
- [ ] AI 回應在 30 秒內顯示
- [ ] 回應是 Markdown 格式並正確渲染

---

**測試 ID**: FE-INTERACT-003 (新增計劃)

1. 前往日誌頁面
2. 切換到「交易計劃」頁籤
3. 點擊「新增計劃」
4. 填寫表單並提交

**驗證點**:
- [ ] 表單驗證正常
- [ ] 提交後計劃出現在列表

---

### 3.3 自動更新

**測試 ID**: FE-AUTO-001 (價格更新)

1. 在儀表板觀察「價格更新於」時間戳
2. 等待 60 秒

**驗證點**:
- [ ] 時間戳更新
- [ ] 持倉價格可能更新

---

## 4. 整合測試用例

### 4.1 完整交易流程

**測試 ID**: INT-TRADE-001

1. **同步數據**
   ```bash
   curl -X POST "http://localhost:8000/api/ibkr/sync"
   ```
   驗證: success = true

2. **檢查持倉**
   ```bash
   curl "http://localhost:8000/api/portfolio"
   ```
   驗證: positions 不為空

3. **檢查統計**
   ```bash
   curl "http://localhost:8000/api/statistics"
   ```
   驗證: total_trades > 0

4. **AI 分析**
   ```bash
   curl -X POST "http://localhost:8000/api/ai/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "分析我的整體風險"}'
   ```
   驗證: 收到 AI 回應

---

### 4.2 MFE/MAE 完整流程

**測試 ID**: INT-MFEMAE-001

1. **計算 MFE/MAE**
   ```bash
   curl -X POST "http://localhost:8000/api/mfe-mae/calculate?recalculate=true"
   ```

2. **取得統計**
   ```bash
   curl "http://localhost:8000/api/mfe-mae/stats"
   ```
   驗證: total_records > 0

3. **取得 AI 建議**
   ```bash
   curl "http://localhost:8000/api/mfe-mae/ai-advice"
   ```
   驗證: 收到改進建議

---

### 4.3 日誌完整流程

**測試 ID**: INT-JOURNAL-001

1. **AI 生成計劃**
   ```bash
   curl -X POST "http://localhost:8000/api/trade-plans/generate" \
     -H "Content-Type: application/json" \
     -d '{"symbol": "AAPL", "direction": "long"}'
   ```
   記錄返回的 plan content

2. **儲存計劃**
   ```bash
   curl -X POST "http://localhost:8000/api/trade-plans" \
     -H "Content-Type: application/json" \
     -d '<從步驟 1 取得的內容>'
   ```
   記錄 plan_id

3. **取得 AI 評價**
   ```bash
   curl "http://localhost:8000/api/trade-plans/{plan_id}/ai-review"
   ```
   驗證: 收到評價內容

4. **AI 生成日誌**
   ```bash
   curl -X POST "http://localhost:8000/api/trade-notes/generate" \
     -H "Content-Type: application/json" \
     -d '{"note_type": "daily", "date": "2024-12-16"}'
   ```
   驗證: 收到日誌草稿

---

## 5. 錯誤處理測試

### 5.1 無效輸入

**測試 ID**: ERR-INPUT-001 (無效日期)

```bash
curl "http://localhost:8000/api/statistics?start_date=invalid"
```

**預期**: HTTP 422 或 400，帶有錯誤訊息

---

**測試 ID**: ERR-INPUT-002 (缺少必要欄位)

```bash
curl -X POST "http://localhost:8000/api/trade-plans" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**預期**: HTTP 422，說明缺少 symbol

---

### 5.2 資源不存在

**測試 ID**: ERR-404-001 (計劃不存在)

```bash
curl "http://localhost:8000/api/trade-plans/999999"
```

**預期**: HTTP 404

---

### 5.3 IBKR 錯誤處理

**測試 ID**: ERR-IBKR-001 (無效 Token)

```bash
curl -X POST "http://localhost:8000/api/config/validate" \
  -H "Content-Type: application/json" \
  -d '{"config_type": "ibkr", "token": "invalid_token"}'
```

**預期**: success = false，message 說明錯誤原因

---

### 5.4 AI 錯誤處理

**測試 ID**: ERR-AI-001 (無效 API Key)

當 GEMINI_API_KEY 無效時：

```bash
curl -X POST "http://localhost:8000/api/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "測試"}'
```

**預期**: HTTP 500 或 503，帶有明確錯誤訊息

---

## 6. 效能測試

### 6.1 回應時間

**測試 ID**: PERF-001 (API 回應)

對以下端點測量回應時間：

| 端點 | 預期回應時間 |
|------|--------------|
| GET /health | < 100ms |
| GET /api/statistics | < 500ms |
| GET /api/portfolio | < 1s |
| POST /api/ai/chat | < 30s |

```bash
# 使用 time 測量
time curl http://localhost:8000/api/statistics
```

---

### 6.2 並發測試

**測試 ID**: PERF-002 (並發請求)

```bash
# 使用 ab (Apache Bench) 測試
ab -n 100 -c 10 http://localhost:8000/api/statistics
```

**預期**: 
- 無請求失敗
- 平均回應時間 < 1s

---

## 附錄

### A. 測試工具

推薦的測試工具：
- **curl**: 基本 API 測試
- **Postman**: GUI API 測試
- **pytest**: Python 單元測試
- **Playwright/Cypress**: 前端 E2E 測試
- **ab (Apache Bench)**: 效能測試

### B. CI/CD 整合

```yaml
# 範例 GitHub Actions
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start server
        run: uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
      - name: Run tests
        run: pytest tests/
```

### C. 測試報告範本

```markdown
# 測試報告

## 概要
- 測試日期: YYYY-MM-DD
- 測試人員: XXX
- 環境: Development / Staging / Production

## 結果摘要
- 總測試數: XX
- 通過: XX
- 失敗: XX
- 跳過: XX

## 失敗詳情
| 測試 ID | 失敗原因 | 嚴重度 |
|---------|----------|--------|
| XXX-001 | 描述... | High |

## 建議
- ...
```

---

**文件結束**
