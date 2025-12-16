# AI Trading Journal - IBKR 整合與資料驗證技術文件

> **版本**: 2.0.0  
> **最後更新**: 2024-12-16  
> **文件目的**: 說明 IBKR 整合的技術細節、常見錯誤處理和資料驗證機制

---

## 目錄

1. [IBKR Flex Query 概述](#1-ibkr-flex-query-概述)
2. [資料安全解析](#2-資料安全解析)
3. [常見錯誤與處理](#3-常見錯誤與處理)
4. [日期格式處理](#4-日期格式處理)
5. [負值處理](#5-負值處理)
6. [驗證機制](#6-驗證機制)
---

## ⚠️ 重要：資料來源分工

### 設計原則

本系統將資料來源明確分為兩部分：

| 資料來源 | 職責 | 更新頻率 |
|----------|------|----------|
| **IBKR Flex Query** | 交易記錄、持倉數量、成本基礎、現金餘額 | 手動同步 |
| **Yahoo Finance (yfinance)** | **即時股票價格** | 每 60 秒自動 |

### 運作方式

```
┌─────────────────────────────────────────────────────────────────┐
│                    價格更新流程 (每 60 秒)                        │
├─────────────────────────────────────────────────────────────────┤
│  1. 前端 React Query 觸發 GET /api/portfolio                    │
│  2. 後端讀取 IBKR 持倉快照（數量、成本）                          │
│  3. 後端從 yfinance 獲取即時股價 ← 關鍵步驟                      │
│  4. 重新計算未實現盈虧                                          │
│  5. 返回更新後的 portfolio                                      │
└─────────────────────────────────────────────────────────────────┘
```

### IBKR 不負責的事項

- ❌ **股票即時價格**：由 yfinance 提供
- ❌ **價格自動更新**：IBKR 快照是靜態的

### IBKR 負責的事項

- ✅ 交易記錄匯入
- ✅ 持倉數量和部位方向
- ✅ 成本基礎（平均成本）
- ✅ 現金餘額
- ✅ 選擇權詳細資訊（Strike、Expiry、Put/Call）

---


## 1. IBKR Flex Query 概述

### 1.1 什麼是 Flex Query

IBKR Flex Query 是 Interactive Brokers 提供的報表服務，允許用戶自訂要取得的資料欄位和格式。

### 1.2 API 流程

```
1. 發送請求 (SendRequest)
   ↓
2. 取得 Reference Code
   ↓
3. 等待報表生成 (5-15 秒)
   ↓
4. 取得報表 (GetStatement)
   ↓
5. 解析 XML/CSV
```

### 1.3 支援的 Query 類型

| Query 類型 | 環境變數 | 用途 |
|-----------|----------|------|
| 交易歷史 | IBKR_HISTORY_QUERY_ID | 匯入交易記錄 |
| 持倉快照 | IBKR_POSITIONS_QUERY_ID | 同步當前持倉 |

### 1.4 必要欄位

#### 交易歷史 Query

必要欄位：
- Symbol
- TradeDate
- Quantity  
- TradePrice
- IBCommission
- AssetClass
- Buy/Sell

選填欄位：
- DateTime
- Proceeds
- Strike
- Expiry
- Put/Call
- Multiplier
- UnderlyingSymbol
- FifoPnlRealized

#### 持倉快照 Query

必要欄位：
- Symbol
- Quantity
- MarkPrice
- CostBasisPrice
- AssetClass

選填欄位：
- Strike
- Expiry
- Put/Call
- Multiplier
- FifoPnlUnrealized
- PositionValue

---

## 2. 資料安全解析

### 2.1 問題背景

IBKR 返回的資料可能包含：
- **空值**: `None`, `""`, `"nan"`, `"-"`
- **異常值**: 無法解析的字串、負數價格
- **格式不一致**: 日期格式多樣

### 2.2 安全解析函數

位置：`utils/validators.py`

#### safe_float()

```python
def safe_float(
    value: Any, 
    default: float = 0.0, 
    allow_negative: bool = True
) -> float:
    """
    安全地將值轉換為 float
    
    處理情況：
    - None, NaN, 空字串 → 返回 default
    - 無法解析的字串 → 返回 default
    - 負值 → 根據 allow_negative 決定是否取絕對值
    
    範例：
        safe_float("123.45") → 123.45
        safe_float("") → 0.0
        safe_float(None) → 0.0
        safe_float("-5.0", allow_negative=False) → 5.0
    """
```

#### safe_int()

```python
def safe_int(
    value: Any, 
    default: int = 0, 
    allow_negative: bool = True
) -> int:
    """
    安全地將值轉換為 int
    
    範例：
        safe_int("100") → 100
        safe_int("100.5") → 100
        safe_int(None) → 0
    """
```

#### safe_date_parse()

```python
def safe_date_parse(
    date_str: Any, 
    formats: Optional[List[str]] = None
) -> Optional[str]:
    """
    安全地解析日期字串並返回標準格式 (YYYY-MM-DD)
    
    支援格式：
    - YYYYMMDD (最常見)
    - YYYY-MM-DD
    - YYYYMMDD;HHMMSS
    - YYYY/MM/DD
    
    範例：
        safe_date_parse("20241215") → "2024-12-15"
        safe_date_parse("2024-12-15") → "2024-12-15"
        safe_date_parse("20241215;093000") → "2024-12-15"
        safe_date_parse(None) → None
        safe_date_parse("invalid") → None
    """
```

### 2.3 使用範例

```python
from utils.validators import safe_float, safe_int, safe_date_parse

# 解析 IBKR 返回的資料
position = {
    'quantity': safe_float(ibkr_data.get('position'), 0),
    'mark_price': safe_float(ibkr_data.get('markPrice'), 0, allow_negative=False),
    'average_cost': safe_float(ibkr_data.get('costBasisPrice'), 0, allow_negative=False),
    'unrealized_pnl': safe_float(ibkr_data.get('fifoPnlUnrealized'), 0),
}

trade_date = safe_date_parse(ibkr_data.get('tradeDate'))
```

---

## 3. 常見錯誤與處理

### 3.1 API 錯誤

| 錯誤碼 | 說明 | 處理方式 |
|--------|------|----------|
| 1012 | Token 無效 | 檢查 IBKR_FLEX_TOKEN |
| 1013 | Query ID 無效 | 檢查 Query ID 設定 |
| 1019 | 報表尚未準備好 | 增加等待時間後重試 |

#### 處理範例

```python
def _request_report(self, query_id: str) -> str:
    try:
        response = self.session.get(url, params=params, timeout=30)
        root = ET.fromstring(response.content)
        
        status = root.find('.//Status').text
        if status != 'Success':
            error_code = root.find('.//ErrorCode').text
            error_msg = root.find('.//ErrorMessage').text
            raise Exception(f"Flex Query 請求失敗: {error_code} - {error_msg}")
        
        return root.find('.//ReferenceCode').text
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"網路請求失敗: {str(e)}")
    except ET.ParseError as e:
        raise Exception(f"XML 解析失敗: {str(e)}")
```

### 3.2 資料解析錯誤

#### 空值處理

**錯誤範例**:
```python
# 危險！如果欄位為空會拋出 ValueError
price = float(data.get('markPrice'))
```

**正確做法**:
```python
# 安全！空值會返回預設值
price = safe_float(data.get('markPrice'), 0, allow_negative=False)
```

#### CSV 解析錯誤

IBKR CSV 格式特殊，包含控制行（BOF, BOA, BOS, EOS, EOA, EOF）。

```python
def _parse_positions_csv(self, csv_content: str) -> List[Dict]:
    lines = csv_content.strip().split('\n')
    
    for line in lines:
        # 跳過控制行
        if line.startswith('"BO') or line.startswith('"EO'):
            continue
        
        # 解析資料行
        ...
```

### 3.3 網路錯誤

```python
try:
    response = self.session.get(url, params=params, timeout=30)
    response.raise_for_status()
except requests.exceptions.Timeout:
    raise Exception("IBKR API 連線逾時，請稍後重試")
except requests.exceptions.ConnectionError:
    raise Exception("無法連接 IBKR API，請檢查網路連線")
```

---

## 4. 日期格式處理

### 4.1 IBKR 日期格式

IBKR 使用多種日期格式：

| 欄位 | 格式 | 範例 |
|------|------|------|
| TradeDate | YYYYMMDD | 20241215 |
| DateTime | YYYYMMDD;HHMMSS | 20241215;093045 |
| Expiry | YYYYMMDD | 20241220 |
| fromDate/toDate | YYYYMMDD | 20241201 |

### 4.2 處理邏輯

```python
def safe_date_parse(date_str: Any, formats: Optional[List[str]] = None) -> Optional[str]:
    if date_str is None:
        return None
    
    date_str = str(date_str).strip()
    if not date_str or date_str.lower() in ['nan', 'none', 'null']:
        return None
    
    # 處理 DateTime 格式 (YYYYMMDD;HHMMSS)
    if ';' in date_str:
        date_str = date_str.split(';')[0]
    
    # 嘗試解析 YYYYMMDD
    if len(date_str) >= 8 and date_str[:8].isdigit():
        year = date_str[0:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    
    # 嘗試其他格式
    for fmt in ['%Y-%m-%d', '%Y/%m/%d']:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None
```

### 4.3 選擇權到期日特殊處理

選擇權 symbol 通常包含到期日：

```
AAPL 241220C185
     ^^^^^^
     YYMMDD = 2024-12-20
```

解析方式：
```python
def parse_option_symbol(symbol: str) -> dict:
    # 使用正則表達式解析
    match = re.match(r'(\w+)\s+(\d{6})([CP])(\d+)', symbol)
    if match:
        underlying = match.group(1)
        expiry_str = match.group(2)  # YYMMDD
        option_type = 'Call' if match.group(3) == 'C' else 'Put'
        strike = float(match.group(4))
        
        # 轉換到期日
        expiry = f"20{expiry_str[0:2]}-{expiry_str[2:4]}-{expiry_str[4:6]}"
        
        return {
            'underlying': underlying,
            'expiry': expiry,
            'option_type': option_type,
            'strike': strike
        }
```

---

## 5. 負值處理

### 5.1 合法的負值

| 欄位 | 可為負值 | 說明 |
|------|----------|------|
| quantity | 是 | 負數表示空頭部位 |
| unrealized_pnl | 是 | 負數表示虧損 |
| realized_pnl | 是 | 負數表示虧損 |
| commission | 是 | 通常為負 |
| proceeds | 是 | 視買賣而定 |

### 5.2 不應為負的欄位

| 欄位 | 處理方式 |
|------|----------|
| price / mark_price | 取絕對值 |
| average_cost | 取絕對值 |
| strike | 必為正 |
| multiplier | 必為正 |

### 5.3 處理範例

```python
# 允許負值的欄位
quantity = safe_float(data.get('quantity'), 0, allow_negative=True)
unrealized_pnl = safe_float(data.get('fifoPnlUnrealized'), 0, allow_negative=True)

# 不允許負值的欄位
mark_price = safe_float(data.get('markPrice'), 0, allow_negative=False)
average_cost = safe_float(data.get('costBasisPrice'), 0, allow_negative=False)
```

### 5.4 空頭部位處理

空頭部位的 quantity 為負值：

```python
quantity = safe_float(position.get('position'), 0)

if quantity < 0:
    # 這是空頭部位
    action = 'SHORT'
    display_quantity = abs(quantity)
else:
    action = 'LONG'
    display_quantity = quantity
```

---

## 6. 驗證機制

### 6.1 交易資料驗證

位置：`utils/validators.py` - `TradeValidator` 類

```python
class TradeValidator:
    VALID_ACTIONS = {'BUY', 'SELL', 'BOT', 'SLD'}
    VALID_INSTRUMENT_TYPES = {'stock', 'option', 'futures'}
    
    @staticmethod
    def validate_trade(trade: Dict) -> Tuple[bool, List[str]]:
        errors = []
        
        # 必要欄位
        required = ['datetime', 'symbol', 'action', 'quantity', 'price']
        for field in required:
            if not trade.get(field):
                errors.append(f"缺少必要欄位: {field}")
        
        # 價格驗證
        if 'price' in trade:
            try:
                price = float(trade['price'])
                if price <= 0:
                    errors.append("價格必須大於 0")
            except (ValueError, TypeError):
                errors.append("無效的價格格式")
        
        # 數量驗證
        if 'quantity' in trade:
            try:
                qty = float(trade['quantity'])
                if qty == 0:
                    errors.append("數量不可為 0")
            except (ValueError, TypeError):
                errors.append("無效的數量格式")
        
        return (len(errors) == 0, errors)
```

### 6.2 自動修正

```python
@staticmethod
def auto_fix_trade(trade: Dict) -> Dict:
    fixed = trade.copy()
    
    # 標準化動作
    action = str(fixed.get('action', '')).upper()
    if action == 'BOT':
        fixed['action'] = 'BUY'
    elif action == 'SLD':
        fixed['action'] = 'SELL'
    
    # 標準化選擇權類型
    opt_type = str(fixed.get('option_type', '')).upper()
    if opt_type == 'C':
        fixed['option_type'] = 'Call'
    elif opt_type == 'P':
        fixed['option_type'] = 'Put'
    
    # 修正 multiplier
    if fixed.get('instrument_type') == 'option':
        fixed['multiplier'] = 100
    else:
        fixed['multiplier'] = 1
    
    return fixed
```

### 6.3 Flex Query 設定驗證

```python
class FlexQueryValidator:
    REQUIRED_FIELDS = {
        'trades': ['Symbol', 'TradeDate', 'Quantity', 'TradePrice', 
                   'IBCommission', 'AssetClass', 'Buy/Sell'],
        'positions': ['Symbol', 'Quantity', 'MarkPrice', 
                      'CostBasisPrice', 'AssetClass'],
    }
    
    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, query_type: str):
        schema = cls.REQUIRED_FIELDS.get(query_type, [])
        
        missing = []
        for field in schema:
            if field not in df.columns:
                missing.append(field)
        
        return {
            'is_valid': len(missing) == 0,
            'missing_fields': missing,
        }
```

---

## 附錄

### A. 錯誤訊息對照表

| 錯誤訊息 | 可能原因 | 解決方法 |
|----------|----------|----------|
| "IBKR_FLEX_TOKEN 未設定" | 環境變數未設定 | 在 .env 或設定頁面設定 Token |
| "Query ID 無效" | Query ID 錯誤或不存在 | 確認 IBKR Portal 中的 Query ID |
| "報表尚未準備好" | 報表生成中 | 等待 10 秒後重試 |
| "XML 解析失敗" | IBKR 返回非預期格式 | 檢查 Query 設定 |
| "網路請求失敗" | 網路問題 | 檢查網路連線 |

### B. 調試技巧

1. **啟用詳細日誌**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **保存原始回應**:
   ```python
   with open('ibkr_response.xml', 'w') as f:
       f.write(response.text)
   ```

3. **測試單一函數**:
   ```python
   from utils.validators import safe_float, safe_date_parse
   
   # 測試
   print(safe_float(""))  # 應返回 0.0
   print(safe_date_parse("20241215"))  # 應返回 "2024-12-15"
   ```

### C. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 2.0.0 | 2024-12-16 | 添加 safe_float, safe_int, safe_date_parse |
| 1.0.0 | 2024-11-01 | 初始版本 |

---

**文件結束**
