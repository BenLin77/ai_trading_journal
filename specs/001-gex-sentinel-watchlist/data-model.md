# Data Model: GEX Sentinel Watchlist Dashboard

**Feature**: 001-gex-sentinel-watchlist
**Date**: 2025-11-20
**Source**: Entities from [spec.md](./spec.md) + [research.md](./research.md) schema decisions

## Entities

### 1. WatchlistEntry

**Purpose**: Represents a user-tracked stock symbol in the monitoring list.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | int | PK, AUTO_INCREMENT | Unique identifier for database row |
| `symbol` | str | UNIQUE, NOT NULL | Stock ticker (e.g., "NVDA", "AMD") |
| `added_at` | datetime | DEFAULT=NOW() | Timestamp when symbol was added |
| `category` | str | NULLABLE | Optional grouping (e.g., "Tech", "Core") |
| `notes` | str | NULLABLE | User annotations (future enhancement) |
| `enabled` | bool | DEFAULT=True | Active/inactive flag (future: disable without deleting) |

**Validation Rules**:
- `symbol` must be uppercase (enforce in service layer)
- `symbol` must be valid ticker (validated via yfinance before insert)
- `category` limited to predefined list (if P4 implemented): ["Tech", "Core", "Speculative", null]

**Relationships**:
- None (watchlist is independent; GEX data fetched on-demand)

**State Transitions**:
```
[User Input] → VALIDATE → [Added] → [Enabled]
                ↓              ↓
            [Error]         [Disabled]
                            → [Removed]
```

---

### 2. GEXProfile

**Purpose**: Calculated market structure snapshot for a single symbol (derived, not persisted).

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `symbol` | str | NOT NULL | Stock ticker |
| `net_gex` | float | NOT NULL | Net gamma exposure in dollars (calls - puts) |
| `gex_state` | str | ENUM | "Bullish" (net_gex > 0) or "Bearish" (net_gex < 0) |
| `call_wall` | float | NULLABLE | Strike with highest call open interest |
| `put_wall` | float | NULLABLE | Strike with highest put open interest |
| `max_pain` | float | NULLABLE | Strike with minimum total intrinsic value |
| `timestamp` | datetime | NOT NULL | When calculation was performed |

**Validation Rules**:
- `gex_state` derived from sign of `net_gex`
- `call_wall` and `put_wall` must be valid strikes from options chain
- `max_pain` must be within active strike range

**Relationships**:
- Linked to `WatchlistEntry` by `symbol` (lookup key, not foreign key)
- Contains multiple `Strike` records (options chain) used in calculation

**Derivation Logic**:
```python
net_gex = sum(call_gex_per_strike) - sum(put_gex_per_strike)
gex_state = "Bullish" if net_gex > 0 else "Bearish"
call_wall = max(call_strikes, key=lambda s: s.open_interest)
put_wall = max(put_strikes, key=lambda s: s.open_interest)
max_pain = min(all_strikes, key=lambda s: intrinsic_value_loss(s))
```

---

### 3. MarketSnapshot

**Purpose**: Current price and change data for a symbol (derived, not persisted).

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `symbol` | str | NOT NULL | Stock ticker |
| `current_price` | float | NOT NULL | Latest trade price |
| `previous_close` | float | NOT NULL | Prior session close |
| `change_pct` | float | NOT NULL | Percentage change (current - prev) / prev |
| `timestamp` | datetime | NOT NULL | When data was fetched |

**Validation Rules**:
- `change_pct` = (current_price - previous_close) / previous_close * 100
- `current_price` and `previous_close` must be positive

**Relationships**:
- Linked to `WatchlistEntry` by `symbol`
- Combined with `GEXProfile` in scanner table display

---

### 4. SentimentIndicators

**Purpose**: Technical indicators for momentum and options positioning (derived, not persisted).

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `symbol` | str | NOT NULL | Stock ticker |
| `rsi` | float | RANGE=[0, 100] | Relative Strength Index (14-period) |
| `pcr` | float | NOT NULL | Put/Call Ratio (total put OI / total call OI) |
| `iv_percentile` | float | RANGE=[0, 100] | Implied Volatility rank vs 52-week history |
| `timestamp` | datetime | NOT NULL | When indicators were calculated |

**Validation Rules**:
- `rsi` clamped to [0, 100] range
- `pcr` cannot be negative (0 if no calls, infinity if no puts → cap at 10.0)
- `iv_percentile` = percentile_rank(current_iv, 52_week_iv_history)

**Relationships**:
- Linked to `WatchlistEntry` by `symbol`
- Displayed in deep-dive view alongside `GEXProfile`

**Calculation Notes**:
- **RSI**: Standard 14-period Wilder's RSI on daily close prices
- **PCR**: `sum(put_OI) / sum(call_OI)` across all strikes
- **IV Percentile**: Fetch 52 weeks of historical IV → calculate percentile of current IV

---

### 5. OptionsChain (Internal)

**Purpose**: Raw options data from yfinance API (not persisted, used for calculations).

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | str | Stock ticker |
| `expiry_date` | date | Options expiration date |
| `strike` | float | Strike price |
| `option_type` | str | "call" or "put" |
| `open_interest` | int | Number of open contracts |
| `implied_volatility` | float | IV for this strike (annualized) |
| `last_price` | float | Last traded premium |
| `bid` | float | Current bid price |
| `ask` | float | Current ask price |
| `volume` | int | Daily traded volume |

**Validation Rules**:
- `open_interest` >= 0
- `implied_volatility` >= 0 (can be 0 for illiquid strikes)
- `strike` > 0
- `option_type` in ["call", "put"]

**Relationships**:
- Source data for `GEXProfile` and `SentimentIndicators`
- Fetched from yfinance API, cached for TTL=300s

**Schema Contract** (from research.md):
```python
# yfinance returns OptionChain(calls=DataFrame, puts=DataFrame)
expected_columns = [
    'contractSymbol', 'strike', 'lastPrice', 'bid', 'ask',
    'volume', 'openInterest', 'impliedVolatility'
]
```

---

## Database Schema (SQLite)

### Persisted Tables

Only `watchlist` table is persisted. All other entities are ephemeral (calculated on-demand).

```sql
-- Watchlist Table
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    enabled BOOLEAN DEFAULT 1
);

CREATE INDEX idx_watchlist_category ON watchlist(category);
CREATE INDEX idx_watchlist_enabled ON watchlist(enabled);

-- Future tables (not in scope for 001):
-- CREATE TABLE trades (...);
-- CREATE TABLE positions (...);
-- CREATE TABLE notes (...);
```

### Migration Strategy

```python
# db.py initialization
def initialize_db(conn):
    current_version = conn.execute("PRAGMA user_version;").fetchone()[0]

    if current_version == 0:
        # Initial schema
        conn.execute(CREATE_WATCHLIST_TABLE_SQL)
        conn.execute("PRAGMA user_version = 1;")

    # Future migrations:
    # if current_version == 1:
    #     conn.execute("ALTER TABLE watchlist ADD COLUMN new_field TEXT;")
    #     conn.execute("PRAGMA user_version = 2;")
```

---

## Data Flow

### Add Symbol to Watchlist

```
User Input (UI)
  ↓
Validate Symbol (yfinance.Ticker exists?)
  ↓
Insert WatchlistEntry (DB)
  ↓
Fetch MarketSnapshot (cached)
  ↓
Display in Sidebar
```

### Load Scanner Table

```
Query All Watchlist Entries (DB)
  ↓
For Each Symbol (batch with progress bar):
  ↓
  Fetch OptionsChain (yfinance, cached TTL=300s)
  ↓
  Calculate GEXProfile (net_gex, walls, max_pain)
  ↓
  Fetch MarketSnapshot (current price, change %)
  ↓
Combine All Data → DataFrame
  ↓
Display Scanner Table (Streamlit st.dataframe)
```

### Deep Dive View

```
User Selects Symbol (scanner row click)
  ↓
Fetch GEXProfile (cached from scanner load)
  ↓
Fetch SentimentIndicators (RSI, PCR, IV percentile)
  ↓
Display Structure Card (net_gex, gex_state)
  ↓
Display Walls Card (call_wall, max_pain, put_wall)
  ↓
Display Sentiment Card (RSI gauge, PCR)
  ↓
User Clicks "Analyze Structure" Button
  ↓
Send {symbol, GEXProfile, SentimentIndicators} to LLM API
  ↓
Display AI Analysis Text
```

---

## Caching Strategy

### Cache Keys & TTLs

| Data Type | Cache Key | TTL | Rationale |
|-----------|-----------|-----|-----------|
| `OptionsChain` | `(symbol, expiry_date)` | 300s | Market data changes frequently |
| `GEXProfile` | `(symbol)` | 300s | Derived from options chain |
| `MarketSnapshot` | `(symbol)` | 300s | Price/change data |
| `SentimentIndicators` | `(symbol)` | 300s | Indicators recalculated with fresh data |
| `IV History (52w)` | `(symbol)` | 3600s | Historical data changes slowly |

### Cache Invalidation

- **User-triggered**: "Refresh" button → `st.cache_data.clear()`
- **Auto-expiry**: TTL expiration
- **Error-triggered**: API failure → mark stale, retry after 60s

---

## Edge Case Handling

### Missing Data

| Scenario | Behavior |
|----------|----------|
| Symbol has no options chain | Display "N/A" for GEX fields, show warning icon |
| OI data missing for all strikes | Cannot calculate GEX → show "Insufficient Data" |
| IV data missing | Skip gamma weighting, use raw OI only |
| Market closed | Display last cached data with "as of [timestamp]" |
| Delisted symbol | Remove from watchlist with notification |

### Boundary Conditions

| Condition | Validation |
|-----------|------------|
| Net GEX = 0 exactly | Label as "Neutral" instead of Bullish/Bearish |
| PCR = infinity (no calls) | Cap PCR display at 10.0, show "Extreme Put Skew" |
| RSI = NaN (insufficient price history) | Display "—" (em dash), tooltip: "Need 14+ days data" |
| Empty watchlist | Show onboarding message instead of scanner table |

---

## Summary

### Key Design Decisions

1. **Minimal Persistence**: Only `watchlist` table persisted; all metrics calculated on-demand
2. **Cache-First**: 5-minute TTL balances freshness with performance (SC-003: <1s cached load)
3. **Graceful Degradation**: Missing data → "N/A" with tooltip, not hard errors
4. **Extensible Schema**: Future-proof columns (`notes`, `enabled`) avoid migrations

### Constitution Alignment

- ✅ **Privacy (Principle I)**: No user data in derived entities, only local SQLite
- ✅ **Performance (Principle III)**: Aggressive caching reduces API load to ~4 calls/symbol/5min
- ✅ **Structure First (Principle IV)**: `GEXProfile` and `SentimentIndicators` prioritize volatility metrics
- ✅ **Testable (Principle V)**: Clear derivation logic enables unit testing of calculations
