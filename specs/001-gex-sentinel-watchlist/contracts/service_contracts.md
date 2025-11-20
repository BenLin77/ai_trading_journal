# Service Contracts: GEX Sentinel Watchlist Dashboard

**Feature**: 001-gex-sentinel-watchlist
**Date**: 2025-11-20
**Purpose**: Define function signatures and data contracts for all services

---

## 1. Watchlist Service

**Module**: `src/services/watchlist_service.py`

### 1.1 `add_symbol(symbol: str, category: str = None) -> WatchlistEntry`

**Purpose**: Add a new symbol to the watchlist after validation.

**Input**:
```python
symbol: str          # Ticker symbol (e.g., "NVDA")
category: str = None # Optional category ("Tech", "Core", etc.)
```

**Output**:
```python
WatchlistEntry(
    id=int,
    symbol=str,
    added_at=datetime,
    category=str | None,
    enabled=bool
)
```

**Errors**:
- `ValueError`: If symbol is invalid (not found via yfinance)
- `sqlite3.IntegrityError`: If symbol already exists (UNIQUE constraint)

**Preconditions**:
- Database initialized with `watchlist` table
- `symbol` is uppercase and non-empty

**Postconditions**:
- New row inserted in `watchlist` table
- Symbol appears in UI sidebar immediately

---

### 1.2 `remove_symbol(symbol: str) -> bool`

**Purpose**: Remove a symbol from the watchlist.

**Input**:
```python
symbol: str  # Ticker to remove
```

**Output**:
```python
bool  # True if deleted, False if symbol not found
```

**Errors**:
- None (gracefully handles missing symbols)

**Postconditions**:
- Row deleted from `watchlist` table
- Symbol removed from UI sidebar

---

### 1.3 `get_all_symbols() -> List[WatchlistEntry]`

**Purpose**: Retrieve all symbols in the watchlist.

**Input**: None

**Output**:
```python
List[WatchlistEntry]  # Ordered by added_at DESC (newest first)
```

**Errors**:
- `sqlite3.Error`: Database connection failure

**Postconditions**: None (read-only)

---

### 1.4 `get_symbols_by_category(category: str) -> List[WatchlistEntry]`

**Purpose**: Filter watchlist by category (P4 user story).

**Input**:
```python
category: str  # e.g., "Tech", "Core"
```

**Output**:
```python
List[WatchlistEntry]  # Symbols with matching category
```

**Errors**: None

**Postconditions**: None (read-only)

---

## 2. Market Data Service

**Module**: `src/services/market_data_service.py`

### 2.1 `fetch_options_chain(symbol: str, expiry: str = "nearest") -> OptionsChain`

**Purpose**: Fetch options chain data for a symbol (cached 5 min).

**Input**:
```python
symbol: str        # Ticker symbol
expiry: str = "nearest"  # "nearest" or specific date "2025-01-17"
```

**Output**:
```python
OptionsChain(
    symbol=str,
    expiry_date=date,
    calls=pd.DataFrame,  # Columns: strike, openInterest, impliedVolatility, ...
    puts=pd.DataFrame    # Columns: strike, openInterest, impliedVolatility, ...
)
```

**Errors**:
- `ValueError`: Symbol not found or no options available
- `requests.HTTPError`: yfinance API failure (rate limit, network)

**Caching**:
- `@st.cache_data(ttl=300)` on `(symbol, expiry)`
- Key: `f"options_chain_{symbol}_{expiry}"`

**Retry Logic**:
- 3 attempts with exponential backoff (2s, 4s, 8s)
- Circuit breaker after 5 consecutive failures

---

### 2.2 `fetch_price_snapshot(symbol: str) -> MarketSnapshot`

**Purpose**: Fetch current price and previous close (cached 5 min).

**Input**:
```python
symbol: str  # Ticker symbol
```

**Output**:
```python
MarketSnapshot(
    symbol=str,
    current_price=float,
    previous_close=float,
    change_pct=float,
    timestamp=datetime
)
```

**Errors**:
- `ValueError`: Symbol not found
- `requests.HTTPError`: API failure

**Caching**:
- `@st.cache_data(ttl=300)` on `(symbol,)`

---

### 2.3 `fetch_iv_history(symbol: str, period="1y") -> pd.Series`

**Purpose**: Fetch 52-week IV history for percentile calculation (cached 1 hour).

**Input**:
```python
symbol: str           # Ticker symbol
period: str = "1y"    # yfinance period string
```

**Output**:
```python
pd.Series  # Index: dates, Values: IV (annualized)
```

**Errors**:
- `ValueError`: Insufficient historical data (<30 days)

**Caching**:
- `@st.cache_data(ttl=3600)` (1 hour) - historical data changes slowly

---

## 3. GEX Calculator Service

**Module**: `src/services/gex_calculator.py`

### 3.1 `calculate_gex_profile(symbol: str) -> GEXProfile`

**Purpose**: Calculate GEX metrics from options chain (cached 5 min).

**Input**:
```python
symbol: str  # Ticker symbol
```

**Output**:
```python
GEXProfile(
    symbol=str,
    net_gex=float,           # In dollars
    gex_state=str,           # "Bullish" | "Bearish" | "Neutral"
    call_wall=float | None,  # Strike with max call OI
    put_wall=float | None,   # Strike with max put OI
    max_pain=float | None,   # Strike with min intrinsic loss
    timestamp=datetime
)
```

**Errors**:
- `ValueError`: No options chain available (illiquid stock)
- `RuntimeError`: GEX calculation timeout (>2s)

**Algorithm** (from research.md):
```python
# Per-strike GEX
gex_per_strike = OI × gamma × 100 × spot_price² × 0.01

# Net GEX
net_gex = sum(call_gex) - sum(put_gex)

# GEX State
gex_state = "Bullish" if net_gex > 0 else ("Neutral" if net_gex == 0 else "Bearish")

# Walls
call_wall = max(calls['strike'], key=lambda s: calls.loc[s, 'openInterest'])
put_wall = max(puts['strike'], key=lambda s: puts.loc[s, 'openInterest'])

# Max Pain
max_pain = min(all_strikes, key=lambda s: intrinsic_value_loss(s))
```

**Performance Requirement**: Must complete in <2s (PERF-002)

**Caching**:
- `@st.cache_data(ttl=300)` on `(symbol,)`

---

### 3.2 `_calculate_gamma(strike: float, spot: float, iv: float, tte: float) -> float`

**Purpose**: Calculate Black-Scholes gamma for a strike (internal helper).

**Input**:
```python
strike: float  # Strike price
spot: float    # Current stock price
iv: float      # Implied volatility (annualized, 0.0-1.0)
tte: float     # Time to expiry (years)
```

**Output**:
```python
float  # Gamma value
```

**Formula**:
```python
d1 = (log(spot/strike) + (0.025 + 0.5*iv²)*tte) / (iv*sqrt(tte))
gamma = norm.pdf(d1) / (spot * iv * sqrt(tte))
```

**Library**: Use `py_vollib` or `scipy.stats.norm` for `norm.pdf`

---

### 3.3 `_calculate_max_pain(options_chain: OptionsChain) -> float`

**Purpose**: Find strike with minimum total intrinsic value loss (internal helper).

**Input**:
```python
options_chain: OptionsChain  # Calls + puts DataFrames
```

**Output**:
```python
float  # Max Pain strike price
```

**Algorithm**:
```python
for strike in all_strikes:
    call_loss = sum(max(0, spot - s) * oi for s in calls if s > strike)
    put_loss = sum(max(0, s - spot) * oi for s in puts if s < strike)
    total_loss[strike] = call_loss + put_loss

max_pain = min(total_loss, key=total_loss.get)
```

---

## 4. Sentiment Service

**Module**: `src/services/sentiment_service.py`

### 4.1 `calculate_sentiment_indicators(symbol: str) -> SentimentIndicators`

**Purpose**: Calculate RSI, PCR, IV percentile (cached 5 min).

**Input**:
```python
symbol: str  # Ticker symbol
```

**Output**:
```python
SentimentIndicators(
    symbol=str,
    rsi=float,            # 0-100 scale
    pcr=float,            # Put/Call ratio
    iv_percentile=float,  # 0-100 scale (52-week rank)
    timestamp=datetime
)
```

**Errors**:
- `ValueError`: Insufficient data for RSI (need 14+ days)
- `ValueError`: No IV history (illiquid stock)

**Calculations**:
```python
# RSI (14-period Wilder's)
rsi = 100 - (100 / (1 + RS))  # RS = avg_gain / avg_loss

# PCR
pcr = sum(put_OI) / sum(call_OI)  # Cap at 10.0 if calls → 0

# IV Percentile
iv_percentile = percentile_rank(current_iv, iv_52w_history)
```

**Caching**:
- `@st.cache_data(ttl=300)` on `(symbol,)`

---

## 5. Database Service

**Module**: `src/database/db.py`

### 5.1 `get_db_connection() -> sqlite3.Connection`

**Purpose**: Get singleton database connection (cached as resource).

**Input**: None

**Output**:
```python
sqlite3.Connection  # Configured with WAL mode, row_factory
```

**Configuration**:
```python
conn = sqlite3.connect('trading_journal.db', check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL;")  # Prevent corruption
conn.row_factory = sqlite3.Row  # Dict-like access
```

**Caching**:
- `@st.cache_resource` (persists until app restart)

---

### 5.2 `initialize_db() -> None`

**Purpose**: Create schema if not exists, run migrations.

**Input**: None

**Output**: None

**Logic**:
```python
current_version = conn.execute("PRAGMA user_version;").fetchone()[0]

if current_version == 0:
    conn.execute(CREATE_WATCHLIST_TABLE_SQL)
    conn.execute("PRAGMA user_version = 1;")

# Future migrations here
```

**Called**: On app startup (in `pages/6_GEX_Sentinel.py`)

---

## 6. AI Analysis Service

**Module**: `src/services/ai_service.py`

### 6.1 `generate_structure_analysis(symbol: str, gex_profile: GEXProfile, sentiment: SentimentIndicators) -> str`

**Purpose**: Generate AI analysis of market structure.

**Input**:
```python
symbol: str
gex_profile: GEXProfile
sentiment: SentimentIndicators
```

**Output**:
```python
str  # Markdown-formatted analysis text (2-3 paragraphs)
```

**Prompt Template**:
```
You are a market structure analyst. Analyze the following options positioning for {symbol}:

**Gamma Exposure (GEX):**
- Net GEX: ${net_gex:.2f}B
- State: {gex_state}
- Call Wall: ${call_wall}
- Put Wall: ${put_wall}
- Max Pain: ${max_pain}

**Sentiment:**
- RSI: {rsi:.1f}
- PCR: {pcr:.2f}
- IV Percentile: {iv_percentile:.0f}%

Provide:
1. Interpretation of GEX state (bullish/bearish positioning)
2. Significance of walls (support/resistance levels)
3. Sentiment context (overbought/oversold, options skew)
4. Actionable insight (what this structure suggests for price action)
```

**API**:
- Use `os.getenv("LLM_API_KEY")` for authentication
- Endpoint: User-configurable via `.env` (OpenAI, Anthropic, local LLM)

**Timeout**: 5s (per SC-006)

**Errors**:
- `requests.Timeout`: LLM API timeout
- `ValueError`: Missing API key

---

## Contract Testing Requirements

### Unit Tests

Each service must have contract tests verifying:

1. **Input Validation**: Reject invalid inputs (empty symbols, negative values)
2. **Output Schema**: Return values match defined types
3. **Error Handling**: Raise expected exceptions for failure cases
4. **Boundary Conditions**: Handle edge cases (empty data, zero values)

### Integration Tests

1. **yfinance Contract** (`tests/contract/test_yfinance_schema.py`):
   - Assert `option_chain()` returns expected columns
   - Verify data types (float for strike, int for OI)

2. **Database Contract** (`tests/integration/test_database.py`):
   - Verify watchlist table exists
   - Test UNIQUE constraint on symbol
   - Test persistence across connections

### Mock Contracts

For unit tests, mock external dependencies with realistic data:

```python
# Example: Mock yfinance response
mock_options_chain = pd.DataFrame({
    'strike': [100.0, 105.0, 110.0],
    'openInterest': [1000, 1500, 800],
    'impliedVolatility': [0.25, 0.28, 0.30]
})
```

---

## Summary

### Service Dependency Graph

```
UI (Streamlit Pages)
  ↓
├─ Watchlist Service → Database Service
├─ Market Data Service → yfinance API
├─ GEX Calculator → Market Data Service
├─ Sentiment Service → Market Data Service
└─ AI Analysis Service → LLM API
```

### Caching Summary

| Service | Cache Type | TTL | Key |
|---------|-----------|-----|-----|
| Market Data | `@st.cache_data` | 300s | `(symbol, [expiry])` |
| GEX Calculator | `@st.cache_data` | 300s | `(symbol,)` |
| Sentiment | `@st.cache_data` | 300s | `(symbol,)` |
| IV History | `@st.cache_data` | 3600s | `(symbol,)` |
| Database | `@st.cache_resource` | ∞ | N/A |

### Performance Targets

| Operation | Target | Measured By |
|-----------|--------|-------------|
| Add Symbol | <3s | SC-001 |
| GEX Calculation | <2s | SC-004, PERF-002 |
| Scanner Load (20 symbols, cached) | <1s | SC-003 |
| Scanner Load (20 symbols, initial) | <10s | SC-002 |
| AI Analysis | <5s | SC-006 |
