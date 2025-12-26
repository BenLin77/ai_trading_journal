# 多租戶系統實作計劃

> **狀態**: 待實作  
> **優先級**: 中  
> **預估工時**: 8-12 小時  
> **建立日期**: 2025-12-26

## 目標

實現完整的多租戶數據隔離，確保不同用戶登入後只能看到自己的數據。

---

## 一、資料庫變更

### 1.1 需要添加 `user_id` 欄位的資料表

| 資料表 | 說明 | 變更內容 |
|--------|------|----------|
| `trades` | 交易記錄 | 添加 `user_id TEXT NOT NULL` |
| `open_positions` | 持倉快照 | 添加 `user_id TEXT NOT NULL` |
| `cash_snapshots` | 現金餘額快照 | 添加 `user_id TEXT NOT NULL` |
| `journal` | 交易日誌 | 添加 `user_id TEXT NOT NULL` |
| `mistakes` | 錯誤卡片 | 添加 `user_id TEXT NOT NULL` |
| `trade_plans` | 交易計劃 | 添加 `user_id TEXT NOT NULL` |
| `trade_notes` | 交易筆記 | 添加 `user_id TEXT NOT NULL` |
| `mfe_mae_records` | MFE/MAE 記錄 | 添加 `user_id TEXT NOT NULL` |
| `chat_history` | AI 對話記錄 | 添加 `user_id TEXT NOT NULL` |
| `settings` | 系統設定 | 添加 `user_id TEXT`（可為 NULL 表示全局預設）|
| `backtest_results` | 回測結果 | 添加 `user_id TEXT NOT NULL` |
| `ohlc_cache` | K 線緩存 | **不需要** (公共市場數據) |

### 1.2 資料庫遷移腳本

```python
# services/migrations/add_user_id.py

def migrate_add_user_id(db):
    """添加 user_id 欄位到所有需要隔離的資料表"""
    tables_to_migrate = [
        'trades',
        'open_positions', 
        'cash_snapshots',
        'journal',
        'mistakes',
        'trade_plans',
        'trade_notes',
        'mfe_mae_records',
        'chat_history',
        'settings',
    ]
    
    conn = db._get_connection()
    cursor = conn.cursor()
    
    for table in tables_to_migrate:
        # 檢查欄位是否已存在
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print(f"Adding user_id to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT")
            
            # 將現有數據分配給預設用戶
            cursor.execute(f"UPDATE {table} SET user_id = 'user_ben' WHERE user_id IS NULL")
    
    # 創建索引以優化查詢
    for table in tables_to_migrate:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user_id ON {table}(user_id)")
        except Exception as e:
            print(f"Index creation warning for {table}: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed!")
```

---

## 二、後端 API 變更

### 2.1 認證中間件

創建一個依賴注入函數，從 JWT Token 中提取當前用戶：

```python
# backend/auth_middleware.py

from fastapi import Request, HTTPException, Depends
from services.auth_service import verify_token

async def get_current_user(request: Request) -> dict:
    """
    從 Authorization header 中提取並驗證 JWT token
    返回用戶資訊 dict，包含 user_id, username, display_name
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授權")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Token 無效或已過期")
    
    return {
        "user_id": payload.get("sub"),
        "username": payload.get("username"),
        "display_name": payload.get("display_name")
    }


def get_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """簡化版：只返回 user_id"""
    return current_user["user_id"]
```

### 2.2 API 端點修改範例

**修改前（全局數據）：**
```python
@app.get("/api/trades")
async def get_trades(symbol: Optional[str] = None, limit: int = 100):
    trades = db.get_trades(symbol=symbol)
    return trades[:limit]
```

**修改後（按用戶過濾）：**
```python
@app.get("/api/trades")
async def get_trades(
    symbol: Optional[str] = None, 
    limit: int = 100,
    user_id: str = Depends(get_user_id)  # 注入當前用戶
):
    trades = db.get_trades(symbol=symbol, user_id=user_id)  # 傳入 user_id
    return trades[:limit]
```

### 2.3 需要修改的 API 端點清單

| 類別 | 端點 | 說明 |
|------|------|------|
| **交易** | GET /api/trades | 過濾用戶的交易記錄 |
| | GET /api/trades/symbols | 只返回用戶交易過的標的 |
| | GET /api/trades/pnl-by-symbol | 按用戶計算盈虧 |
| **持倉** | GET /api/portfolio | 只返回用戶的持倉 |
| | POST /api/ibkr/sync | 同步到用戶的記錄 |
| | GET /api/ibkr/cash | 用戶的現金餘額 |
| **統計** | GET /api/statistics | 用戶的統計數據 |
| | GET /api/equity-curve | 用戶的資金曲線 |
| **報告** | GET /api/report/performance | 用戶的績效報告 |
| | GET /api/reports | 用戶的每日報告 |
| **AI** | POST /api/ai/chat | 用戶的對話歷史 |
| | POST /api/ai/comprehensive-review | 分析用戶的數據 |
| **計劃/筆記** | GET/POST /api/plans | 用戶的交易計劃 |
| | GET/POST /api/notes | 用戶的交易筆記 |
| **MFE/MAE** | GET /api/mfe-mae/* | 用戶的 MFE/MAE 數據 |
| **錯誤卡片** | GET/POST /api/mistakes | 用戶的錯誤記錄 |
| **設定** | GET/POST /api/config/* | 用戶的設定 |

---

## 三、設定優先級邏輯

### 3.1 讀取優先級

```
1. 資料庫 (user_settings 表，按 user_id 查詢)
   ↓ 如果不存在
2. 資料庫 (settings 表，全局預設值，user_id = NULL)
   ↓ 如果不存在
3. 環境變數 (.env 檔案)
   ↓ 如果不存在
4. 程式碼內建預設值
```

### 3.2 實作範例

```python
# services/config_service.py

class ConfigService:
    def __init__(self, db):
        self.db = db
    
    def get_setting(self, key: str, user_id: str = None) -> Optional[str]:
        """
        獲取設定值，優先級：
        1. 用戶級別設定 (user_id 指定)
        2. 全局設定 (user_id = NULL)
        3. 環境變數
        """
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        # 1. 嘗試讀取用戶級別設定
        if user_id:
            cursor.execute(
                "SELECT value FROM settings WHERE key = ? AND user_id = ?",
                (key, user_id)
            )
            row = cursor.fetchone()
            if row and row[0]:
                conn.close()
                return row[0]
        
        # 2. 嘗試讀取全局設定
        cursor.execute(
            "SELECT value FROM settings WHERE key = ? AND user_id IS NULL",
            (key,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
        
        # 3. 讀取環境變數
        return os.getenv(key)
    
    def set_setting(self, key: str, value: str, user_id: str = None):
        """
        設定值（存入資料庫）
        
        Args:
            key: 設定鍵
            value: 設定值
            user_id: 用戶 ID（如果為 None，則為全局設定）
        """
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO settings (key, value, user_id, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(key, user_id) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
        ''', (key, value, user_id))
        
        conn.commit()
        conn.close()
```

### 3.3 需要支援用戶級別的設定項目

| 設定鍵 | 說明 | 是否敏感 |
|--------|------|----------|
| `IBKR_FLEX_TOKEN` | IBKR API Token | ✅ |
| `IBKR_HISTORY_QUERY_ID` | 歷史查詢 ID | ❌ |
| `IBKR_POSITIONS_QUERY_ID` | 持倉查詢 ID | ❌ |
| `GEMINI_API_KEY` | Gemini API Key | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | ✅ |
| `OPENAI_API_KEY` | OpenAI API Key | ✅ |
| `AI_PROVIDER` | AI 提供商選擇 | ❌ |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ✅ |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | ❌ |
| `TELEGRAM_DAILY_TIME` | 每日報告時間 | ❌ |
| `TELEGRAM_ENABLED` | 是否啟用 Telegram | ❌ |
| `DATA_SOURCE` | 數據來源 (QUERY/GATEWAY) | ❌ |

---

## 四、前端變更

### 4.1 API 請求添加 Authorization Header

確保所有 API 請求都帶有 JWT Token：

```typescript
// frontend/src/lib/api.ts

import axios from 'axios';

const api = axios.create({
  baseURL: '',
});

// 請求攔截器：自動添加 Authorization header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 響應攔截器：處理 401 錯誤
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token 過期，清除並跳轉到登入頁
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_id');
      localStorage.removeItem('display_name');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export { api };
```

### 4.2 需要更新的頁面

所有頁面都會自動受益於 axios 攔截器，不需要單獨修改。

---

## 五、測試計劃

### 5.1 單元測試

- [ ] 測試資料庫遷移腳本
- [ ] 測試 `get_current_user` 認證中間件
- [ ] 測試 `ConfigService` 設定優先級邏輯

### 5.2 整合測試

- [ ] 創建兩個測試用戶 A 和 B
- [ ] 用戶 A 創建交易記錄、計劃、筆記
- [ ] 用戶 B 登入，確認看不到用戶 A 的數據
- [ ] 用戶 B 創建自己的數據
- [ ] 用戶 A 登入，確認看不到用戶 B 的數據
- [ ] 測試設定優先級（DB > .env）

### 5.3 安全測試

- [ ] 嘗試在 API 請求中偽造 user_id 參數
- [ ] 嘗試在無 Token 情況下訪問受保護端點
- [ ] 嘗試使用過期 Token 訪問

---

## 六、實作順序建議

1. **Phase 1: 資料庫遷移** (2小時)
   - 撰寫遷移腳本
   - 備份現有資料庫
   - 執行遷移
   - 驗證數據完整性

2. **Phase 2: 認證中間件** (1小時)
   - 實作 `get_current_user` 依賴
   - 實作 `get_user_id` 簡化版

3. **Phase 3: 核心 API 修改** (3小時)
   - 修改 trades API
   - 修改 portfolio API
   - 修改 statistics API

4. **Phase 4: 設定系統重構** (2小時)
   - 實作 `ConfigService`
   - 修改設定相關 API
   - 測試優先級邏輯

5. **Phase 5: 其他 API** (2小時)
   - 修改剩餘的 API 端點
   - 全面測試

6. **Phase 6: 前端適配** (1小時)
   - 添加 axios 攔截器
   - 處理 401 錯誤

---

## 七、回滾計劃

如果實施過程中出現問題：

1. **資料庫回滾**
   ```bash
   cp backup/trading_journal.db.bak trading_journal.db
   ```

2. **程式碼回滾**
   ```bash
   git checkout <previous-commit> -- backend/main.py database.py
   ```

3. **重啟服務**
   ```bash
   sudo systemctl restart journal-ai.service
   ```

---

## 八、注意事項

1. **敏感設定加密**: 考慮對 API Key 等敏感設定進行加密存儲
2. **效能影響**: 添加 user_id 過濾可能影響查詢效能，需要適當的索引
3. **資料備份**: 在進行任何遷移前，務必備份資料庫
4. **向後相容**: 遷移腳本需要處理現有數據（分配給預設用戶）
