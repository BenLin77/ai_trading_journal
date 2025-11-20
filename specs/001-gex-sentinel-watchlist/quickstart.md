# Quickstart: GEX Sentinel Watchlist Dashboard

**Feature**: 001-gex-sentinel-watchlist
**Target Audience**: Developers implementing this feature
**Estimated Setup Time**: 10 minutes

---

## Prerequisites

- Python 3.11+ installed
- `uv` package manager installed ([installation guide](https://github.com/astral-sh/uv))
- Git repository initialized
- Internet connection (for initial package downloads and market data)

---

## 1. Environment Setup (5 min)

### Initialize Python Project

```bash
# From repository root
uv init  # If not already initialized

# Add core dependencies
uv add streamlit pandas numpy yfinance plotly python-dotenv py-vollib

# Add testing dependencies
uv add --dev pytest pytest-mock pytest-cov
```

### Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env file
nano .env
```

Add the following variables:

```bash
# .env file
# LLM API Configuration (for AI analysis feature)
LLM_API_KEY=your-api-key-here
LLM_API_ENDPOINT=https://api.openai.com/v1/chat/completions  # Or Anthropic/local endpoint

# Database Path (optional, defaults to trading_journal.db)
DB_PATH=trading_journal.db

# Cache Settings (optional, defaults in code)
CACHE_TTL_MARKET_DATA=300  # 5 minutes
CACHE_TTL_IV_HISTORY=3600  # 1 hour
```

**IMPORTANT**: Ensure `.env` is in `.gitignore` (already added by constitution setup).

---

## 2. Database Initialization (2 min)

The database will auto-initialize on first run, but you can manually verify:

```bash
# Create database directory if needed
mkdir -p data/

# Run initialization script (will be created during implementation)
uv run python -m src.database.db
```

Expected output:
```
✓ Database initialized at trading_journal.db
✓ Watchlist table created
✓ Schema version: 1
```

---

## 3. Project Structure (Reference)

```
ai_trading_journal/
├── .env                      # ← Create this (git-ignored)
├── .env.example              # ← Template (committed)
├── .gitignore                # ← Already configured
├── pyproject.toml            # ← Created by uv
├── trading_journal.db        # ← Auto-created (git-ignored)
│
├── pages/
│   └── 6_GEX_Sentinel.py     # ← Main Streamlit page (this feature)
│
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── watchlist.py      # WatchlistEntry dataclass
│   │   ├── gex_profile.py    # GEXProfile, MarketSnapshot
│   │   └── sentiment.py      # SentimentIndicators
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── watchlist_service.py
│   │   ├── market_data_service.py
│   │   ├── gex_calculator.py
│   │   ├── sentiment_service.py
│   │   └── ai_service.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── db.py             # SQLite connection & schema
│   │
│   └── ui/
│       ├── __init__.py
│       ├── sidebar.py        # Watchlist management UI
│       ├── scanner_view.py   # Scanner table component
│       └── deep_dive_view.py # Deep dive component
│
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_gex_calculator.py
    │   ├── test_sentiment_service.py
    │   └── test_watchlist_service.py
    ├── integration/
    │   ├── test_market_data_api.py
    │   └── test_database.py
    └── contract/
        └── test_yfinance_schema.py
```

---

## 4. Running the Application (1 min)

### Start Streamlit

```bash
# From repository root
uv run streamlit run pages/6_GEX_Sentinel.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.x:8501
```

### First-Time Use

1. Open `http://localhost:8501` in your browser
2. Sidebar shows "Watchlist (0 symbols)"
3. Enter a ticker (e.g., "NVDA") and click "Add to Watchlist"
4. Wait for initial data fetch (~5-10 seconds)
5. Scanner table appears with GEX metrics

---

## 5. Running Tests (2 min)

### Run All Tests

```bash
# From repository root
uv run pytest tests/

# With coverage report
uv run pytest --cov=src --cov-report=html tests/
```

### Run Specific Test Suite

```bash
# Unit tests only (fast)
uv run pytest tests/unit/

# Integration tests (requires network)
uv run pytest tests/integration/

# Contract tests (validates external API schemas)
uv run pytest tests/contract/
```

### TDD Workflow (Constitution Principle V)

**CRITICAL**: Tests must be written BEFORE implementation.

1. Write test for feature (e.g., `test_calculate_gex_profile()`)
2. Run test → ❌ **FAILS** (no implementation yet)
3. Implement feature (e.g., `calculate_gex_profile()`)
4. Run test → ✅ **PASSES**
5. Refactor if needed, re-run tests

Example:
```bash
# Step 1: Write test
nano tests/unit/test_gex_calculator.py

# Step 2: Verify test fails
uv run pytest tests/unit/test_gex_calculator.py -v  # Should FAIL

# Step 3: Implement feature
nano src/services/gex_calculator.py

# Step 4: Verify test passes
uv run pytest tests/unit/test_gex_calculator.py -v  # Should PASS
```

---

## 6. Development Workflow

### A. Adding a New Symbol to Watchlist

**User Story**: P1 - Watchlist Management

```bash
# 1. Write test (tests/unit/test_watchlist_service.py)
def test_add_symbol_valid():
    result = watchlist_service.add_symbol("NVDA")
    assert result.symbol == "NVDA"
    assert result.enabled == True

# 2. Implement (src/services/watchlist_service.py)
def add_symbol(symbol: str, category: str = None) -> WatchlistEntry:
    # Validate symbol via yfinance
    ticker = yf.Ticker(symbol)
    if not ticker.info:
        raise ValueError(f"Invalid symbol: {symbol}")

    # Insert into database
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO watchlist (symbol, category) VALUES (?, ?)",
        (symbol.upper(), category)
    )
    # ...

# 3. Wire up UI (pages/6_GEX_Sentinel.py)
with st.sidebar:
    symbol_input = st.text_input("Symbol")
    if st.button("Add to Watchlist"):
        watchlist_service.add_symbol(symbol_input)
        st.success(f"Added {symbol_input}")
```

### B. Calculating GEX Profile

**User Story**: P2 - Scanner Table View

```bash
# 1. Write test (tests/unit/test_gex_calculator.py)
def test_calculate_gex_profile():
    profile = gex_calculator.calculate_gex_profile("NVDA")
    assert profile.net_gex is not None
    assert profile.gex_state in ["Bullish", "Bearish", "Neutral"]
    assert profile.max_pain > 0

# 2. Implement (src/services/gex_calculator.py)
@st.cache_data(ttl=300)
def calculate_gex_profile(symbol: str) -> GEXProfile:
    # Fetch options chain
    chain = fetch_options_chain(symbol)

    # Calculate per-strike GEX
    call_gex = _calculate_strike_gex(chain.calls, spot_price)
    put_gex = _calculate_strike_gex(chain.puts, spot_price)

    net_gex = call_gex.sum() - put_gex.sum()
    # ...

# 3. Display in scanner table
scanner_data = []
for symbol in watchlist:
    gex = calculate_gex_profile(symbol)  # Cached!
    scanner_data.append({
        'Symbol': symbol,
        'GEX State': gex.gex_state,
        'Max Pain': f"${gex.max_pain:.2f}"
    })

st.dataframe(scanner_data)
```

---

## 7. Troubleshooting

### Issue: "Module not found"

**Solution**: Ensure you're running via `uv`:
```bash
uv run streamlit run pages/6_GEX_Sentinel.py
```

### Issue: "yfinance rate limit exceeded"

**Symptoms**: HTTP 429 errors in console

**Solution**:
1. Verify cache is working (check console for cache hits)
2. Reduce watchlist size temporarily
3. Wait 1 hour for rate limit reset

### Issue: "No options chain available for [symbol]"

**Cause**: Symbol has no listed options (e.g., illiquid ETFs, micro-cap stocks)

**Solution**:
- UI shows "N/A" for GEX fields
- Remove symbol from watchlist or use symbols with active options (e.g., AAPL, NVDA, SPY)

### Issue: "Database locked"

**Cause**: SQLite WAL mode not enabled

**Solution**: Verify in `src/database/db.py`:
```python
conn.execute("PRAGMA journal_mode=WAL;")
```

### Issue: "Streamlit cache not working"

**Symptoms**: Slow reloads, API calls on every interaction

**Solution**:
1. Check decorator syntax: `@st.cache_data(ttl=300)` not `@cache_data`
2. Verify Python 3.11+ (required for new cache API)
3. Clear cache: `st.cache_data.clear()` and restart

---

## 8. Key Commands Reference

| Task | Command |
|------|---------|
| **Install dependencies** | `uv add streamlit pandas yfinance ...` |
| **Run application** | `uv run streamlit run pages/6_GEX_Sentinel.py` |
| **Run all tests** | `uv run pytest tests/` |
| **Run unit tests only** | `uv run pytest tests/unit/` |
| **Test with coverage** | `uv run pytest --cov=src --cov-report=html tests/` |
| **Clear Streamlit cache** | Delete `.streamlit/cache/` or use `st.cache_data.clear()` in code |
| **View database** | `sqlite3 trading_journal.db "SELECT * FROM watchlist;"` |
| **Reset database** | `rm trading_journal.db` (will recreate on next run) |

---

## 9. Performance Validation

After implementation, verify performance targets (from [spec.md](./spec.md#success-criteria)):

### Test Scenario 1: Add Symbol (SC-001)

```bash
# Expected: <3 seconds from click to sidebar display
1. Open app
2. Enter "AAPL" in sidebar
3. Click "Add to Watchlist"
4. ✅ Verify: Symbol appears in <3s
```

### Test Scenario 2: Scanner Load (Cached) (SC-003)

```bash
# Expected: <1 second for cached 20-symbol watchlist
1. Load scanner table once (builds cache)
2. Refresh page
3. ✅ Verify: Scanner table renders in <1s
```

### Test Scenario 3: GEX Calculation (SC-004)

```bash
# Expected: <2 seconds per symbol
# Monitor via console logs:
uv run streamlit run pages/6_GEX_Sentinel.py --logger.level=debug

# Add logging in gex_calculator.py:
import time
start = time.time()
# ... calculation ...
print(f"GEX calc for {symbol}: {time.time() - start:.2f}s")

# ✅ Verify: Each symbol <2s
```

---

## 10. Next Steps

1. **Run `/speckit.tasks`** to generate implementation tasks (tasks.md)
2. **Follow TDD workflow** (Principle V): Write tests → Fail → Implement → Pass
3. **Implement User Stories in order**: P1 → P2 → P3 → (P4 optional)
4. **Verify Constitution compliance** at each milestone (see [plan.md](./plan.md#constitution-check))
5. **Manual testing** with real tickers (NVDA, AAPL, SPY, QQQ)

---

## Constitution Compliance Checklist

Before marking feature complete, verify:

- ✅ **Principle I (Privacy)**: `.env` in `.gitignore`, database local-only
- ✅ **Principle II (User Control)**: No auto-population of watchlist
- ✅ **Principle III (Caching)**: All API calls wrapped with `@st.cache_data(ttl=300)`
- ✅ **Principle IV (Structure First)**: GEX/Max Pain displayed prominently
- ✅ **Principle V (Test-First)**: All financial calculations have unit tests

Refer to [constitution.md](../../.specify/memory/constitution.md) for full principles.

---

## Support

- **Feature Spec**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **Service Contracts**: [contracts/service_contracts.md](./contracts/service_contracts.md)
- **Research Decisions**: [research.md](./research.md)
