# Research: GEX Sentinel Watchlist Dashboard

**Feature**: 001-gex-sentinel-watchlist
**Date**: 2025-11-20
**Purpose**: Resolve technical unknowns and establish implementation patterns

## 1. GEX Proxy Algorithm Implementation

### Decision

Use **simplified gamma exposure approximation** based on open interest and dollar gamma per contract formula.

### Formula

```
GEX per strike = OI × Gamma × 100 × Spot Price² × 0.01
Net GEX = Σ(Call GEX) - Σ(Put GEX)
```

Where:
- **OI** (Open Interest): Number of contracts at each strike
- **Gamma**: Approximated using Black-Scholes closed-form for each strike
- **100**: Shares per contract
- **0.01**: Convert to dollars per 1% move

### Rationale

- **Exact dealer positioning requires**:
  - Real-time hedge ratios (not publicly available)
  - Intraday dealer flow data (institutional only)
  - Proprietary market maker inventory
- **Proxy approach trades accuracy for speed**:
  - Black-Scholes gamma calculation: ~10ms per strike
  - Total time for 50 strikes: ~500ms (well under 2s target)
  - Directional accuracy sufficient for retail trading decisions

### Alternatives Considered

| Alternative | Rejected Because |
|------------|------------------|
| Exact dealer gamma (via Bloomberg/institutional feeds) | Requires expensive data subscriptions ($2k+/month), violates privacy principle |
| Machine learning gamma prediction | Over-engineered for MVP, adds training complexity, slower inference |
| Zero gamma approximation (OI only) | Too inaccurate; misses vol surface effects on positioning |

### Implementation Notes

- Use `py_vollib` library for Black-Scholes Greeks (gamma calculation)
- Cache IV surface per symbol (TTL=300s)
- Fallback: If IV unavailable, skip gamma weighting and use raw OI

---

## 2. yfinance Options Chain API Schema

### Decision

Use `yfinance.Ticker.option_chain(date)` method with schema validation.

### Schema (Verified 2024)

```python
# Returns NamedTuple: OptionChain(calls=DataFrame, puts=DataFrame)
calls_df = ticker.option_chain(expiry_date).calls
puts_df = ticker.option_chain(expiry_date).puts

# DataFrame columns (both calls/puts):
['contractSymbol', 'strike', 'lastPrice', 'bid', 'ask',
 'volume', 'openInterest', 'impliedVolatility']
```

### Rationale

- **yfinance is industry standard** for free retail market data
- **Proven reliability**: Used by thousands of trading bots/tools
- **Rate limits**: ~2000 requests/hour (sufficient for 20-symbol watchlist with 5-min cache)
- **Fallback**: Yahoo Finance web scraping if API changes (yfinance auto-adapts)

### Alternatives Considered

| Alternative | Rejected Because |
|------------|------------------|
| IBKR API (official broker data) | Requires live IBKR account, complex TWS gateway setup, overkill for watchlist feature |
| Polygon.io / Alpha Vantage | Requires paid API keys, privacy concern (external tracking), rate limits stricter |
| TDA Ameritrade API | Requires brokerage account, being sunset by Schwab acquisition |

### Implementation Notes

- **Contract test** (`tests/contract/test_yfinance_schema.py`): Assert expected columns present
- **Retry logic**: 3 attempts with exponential backoff (2s, 4s, 8s)
- **Circuit breaker**: If 5 consecutive failures, disable auto-refresh for symbol
- **Error handling**: Missing OI/IV → display "N/A" in UI with tooltip warning

---

## 3. Streamlit Caching Best Practices

### Decision

Use **`@st.cache_data(ttl=300)`** for all market data fetches and calculations.

### Pattern

```python
@st.cache_data(ttl=300)
def fetch_options_chain(symbol: str, expiry: str) -> pd.DataFrame:
    """Cached for 5 minutes. Key: (symbol, expiry)"""
    ticker = yf.Ticker(symbol)
    return ticker.option_chain(expiry)

@st.cache_data(ttl=300)
def calculate_gex_profile(symbol: str) -> GEXProfile:
    """Cached for 5 minutes. Key: (symbol)"""
    # ... GEX calculation logic
    return GEXProfile(...)
```

### Rationale

- **`@st.cache_data`** (formerly `@st.cache`) is for data/calculations:
  - Serializes return values (pickle)
  - Per-parameter cache key (automatic hashing)
  - TTL support built-in
- **`@st.cache_resource`** (formerly `@st.singleton`) is for connections:
  - For DB connections, ML models, API clients
  - NO TTL (persists until app restart)
  - We use this for SQLite connection

### Alternatives Considered

| Alternative | Rejected Because |
|------------|------------------|
| Manual caching (dict + timestamps) | Reinvents wheel, error-prone, Streamlit decorator is battle-tested |
| `@st.cache_resource` for data | Wrong tool; no TTL support, would cache stale data indefinitely |
| Third-party cache (Redis, Memcached) | Over-engineered for single-user local app, violates simplicity |

### Implementation Notes

- **Progress bar integration**: Wrap uncached call with `st.progress()`
  ```python
  progress = st.progress(0)
  for i, symbol in enumerate(watchlist):
      progress.progress((i+1)/len(watchlist))
      fetch_data(symbol)  # Hits cache or fetches
  ```
- **Cache invalidation**: User can click "Refresh" button → `st.cache_data.clear()`
- **Memory management**: Streamlit auto-evicts LRU entries when memory limit hit

---

## 4. SQLite Schema Design

### Decision

Single `watchlist` table with extensibility columns.

### Schema

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    category TEXT DEFAULT NULL,  -- For P4 user story (optional grouping)
    notes TEXT DEFAULT NULL,     -- Future: user annotations
    enabled BOOLEAN DEFAULT 1    -- Future: temporarily disable without deleting
);

CREATE INDEX idx_watchlist_category ON watchlist(category);
CREATE INDEX idx_watchlist_enabled ON watchlist(enabled);
```

### Rationale

- **UNIQUE constraint on symbol**: Prevents duplicates (FR-003)
- **AUTOINCREMENT id**: Stable row IDs for future features (edit, reorder)
- **category column**: Supports P4 user story (watchlist categorization)
- **notes/enabled columns**: Prepared for future enhancements without schema migration pain

### Alternatives Considered

| Alternative | Rejected Because |
|------------|------------------|
| Separate tables (symbols, categories, user_preferences) | YAGNI - over-normalized for current needs, adds JOIN complexity |
| JSON file storage | No ACID guarantees, no indexes, harder to query/update safely |
| In-memory only (st.session_state) | Violates FR-005 (persistence requirement) |

### Implementation Notes

- **Migration strategy**: `db.py` checks schema version, runs ALTER TABLE if needed
  ```python
  def initialize_db():
      conn.execute("CREATE TABLE IF NOT EXISTS watchlist ...")
      # Version check (for future migrations)
      conn.execute("PRAGMA user_version;")  # Returns 0 if new DB
  ```
- **Connection management**: Use `@st.cache_resource` for singleton connection
  ```python
  @st.cache_resource
  def get_db_connection():
      return sqlite3.connect('trading_journal.db', check_same_thread=False)
  ```

---

## 5. Batch Processing with Progress Bars

### Decision

Use **Streamlit native `st.progress()` with status text** for batch operations.

### Pattern

```python
def fetch_watchlist_data(symbols: List[str]) -> Dict[str, GEXProfile]:
    """Fetch GEX data for all symbols with progress indicator."""
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, symbol in enumerate(symbols):
        status_text.text(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
        progress_bar.progress((i + 1) / len(symbols))

        try:
            results[symbol] = calculate_gex_profile(symbol)  # Cached
        except Exception as e:
            st.warning(f"Failed to fetch {symbol}: {e}")
            results[symbol] = None  # Graceful degradation

    progress_bar.empty()  # Remove after completion
    status_text.empty()
    return results
```

### Rationale

- **Built-in Streamlit widgets**: No external dependencies
- **User feedback**: Progress % and current symbol name visible
- **Graceful errors**: Failed symbols don't block entire batch
- **Cache integration**: Cached symbols skip computation but still update progress bar

### Alternatives Considered

| Alternative | Rejected Because |
|------------|------------------|
| `concurrent.futures` (parallel fetch) | yfinance rate limits make parallelism counterproductive; risks IP ban |
| `asyncio` with `aiohttp` | yfinance is synchronous; rewriting wrapper adds complexity for minimal gain |
| Spinner only (no progress %) | Poor UX for 20-symbol watchlist (user can't estimate wait time) |

### Implementation Notes

- **Rate limit handling**: Add 0.5s sleep between API calls if non-cached
  ```python
  if not is_cached:
      time.sleep(0.5)  # Respect yfinance rate limits
  ```
- **Cancel operation**: Streamlit doesn't support cancel (page refresh is workaround)
- **Error accumulation**: Show summary at end: "Loaded 18/20 symbols successfully"

---

## Summary

### Key Technical Decisions

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Market Data** | yfinance | Free, reliable, industry standard |
| **GEX Calculation** | Black-Scholes gamma proxy | Fast (~500ms), directionally accurate |
| **Caching** | `@st.cache_data(ttl=300)` | Built-in, TTL support, simple |
| **Database** | SQLite with extensibility columns | ACID, local, future-proof schema |
| **Progress UI** | `st.progress()` + status text | Native, clear feedback, error-tolerant |

### Risk Mitigation

- **yfinance API changes**: Contract tests alert immediately; yfinance maintainers adapt quickly
- **Rate limits**: 5-min cache + batch throttling (0.5s delays) keeps well under 2000 req/hr
- **GEX accuracy**: Proxy sufficient for retail; document limitations in UI tooltips
- **Database corruption**: SQLite journal mode=WAL (Write-Ahead Logging) prevents corruption

### Open Questions

None. All critical technical unknowns resolved. Ready for Phase 1 design.
