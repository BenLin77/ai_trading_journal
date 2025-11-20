# Implementation Plan: GEX Sentinel Watchlist Dashboard

**Branch**: `001-gex-sentinel-watchlist` | **Date**: 2025-11-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-gex-sentinel-watchlist/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a user-controlled watchlist monitoring system that fetches and calculates market structure metrics (GEX, Max Pain, Volatility) for user-selected stock symbols. System displays a high-level scanner table for quick assessment and detailed deep-dive views for individual symbols with AI-powered structure analysis. Core focus on aggressive caching (5-minute TTL), batch processing with progress indicators, and privacy-first local data storage.

**Technical Approach**: Streamlit web application with SQLite persistence, yfinance for market data, cached computation layer for GEX calculations, and LLM API integration for structure analysis.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Streamlit (UI), yfinance (market data), pandas/numpy (calculations), sqlite3 (storage), plotly (visualizations), python-dotenv (env management)
**Storage**: SQLite database (local file: `trading_journal.db`) with `watchlist` table
**Testing**: pytest (unit tests for GEX calculations), pytest-mock (API mocking)
**Target Platform**: Local desktop (Linux/macOS/Windows), accessed via browser (localhost:8501)
**Project Type**: Single Streamlit application (web UI framework)
**Performance Goals**:
- Scanner table load: <10s for 20 symbols (initial), <1s (cached)
- GEX calculation: <2s per symbol
- Watchlist operations (add/remove): <3s
- AI analysis generation: <5s

**Constraints**:
- Must work offline for cached data (graceful degradation)
- No blocking UI operations (progress bars mandatory for >2s operations)
- Cache TTL: 300s (5min) for real-time data
- Single-user deployment (no concurrency management)

**Scale/Scope**:
- Watchlist size: 5-30 symbols (optimized for 20)
- Concurrent API calls: Batch with progress indicators
- Data retention: Indefinite (local SQLite, user-managed)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Privacy-First Architecture

- ✅ **Watchlist data stored in local SQLite** (FR-005)
- ✅ **No cloud sync or external data transmission** (except API calls for market data)
- ✅ **API keys in .env file** (SEC-001)
- ✅ **.gitignore includes .env, *.db, cache/** (SEC-002, SEC-003)

**Status**: PASS

### ✅ Principle II: User-Controlled Monitoring

- ✅ **Sidebar UI for watchlist management** (FR-001, FR-004)
- ✅ **Explicit add/remove only** (no auto-population) (spec requirement)
- ✅ **User-defined scope** (monitoring limited to watchlist)
- ✅ **Session persistence** (FR-005)

**Status**: PASS

### ✅ Principle III: Performance Through Aggressive Caching (CRITICAL)

- ✅ **@st.cache_data(ttl=300) wrapper for all data fetches** (FR-017)
- ✅ **Progress bars for batch operations** (FR-016)
- ✅ **GEX proxy algorithm** (approximation for speed) (FR-009, FR-025)
- ✅ **<2s per symbol GEX calculation** (PERF-002)

**Status**: PASS

### ✅ Principle IV: Volatility & Structure First

- ✅ **GEX, Max Pain, IV percentile computed** (FR-009, FR-011, FR-013)
- ✅ **Walls (Call/Put OI) displayed** (FR-012, FR-020)
- ✅ **Scanner prioritizes structure over price** (FR-014)

**Status**: PASS

### ✅ Principle V: Test-First for Financial Logic (NON-NEGOTIABLE)

- ✅ **GEX calculation unit tests required** (TDD workflow)
- ✅ **Max Pain calculation unit tests required** (TDD workflow)
- ✅ **Edge cases covered** (missing data, API failures) (FR-024)
- ✅ **Integration tests for yfinance contract** (PERF-004)

**Status**: PASS - Tests must be written BEFORE implementation in `/speckit.tasks`

### Summary

**ALL GATES PASSED** ✅

No violations. Feature design fully aligns with constitution principles I-V. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-gex-sentinel-watchlist/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Streamlit application structure (single project)
pages/
└── 6_GEX_Sentinel.py    # Main Streamlit page for this feature

src/
├── models/
│   ├── watchlist.py     # WatchlistEntry dataclass
│   ├── gex_profile.py   # GEXProfile, MarketSnapshot dataclasses
│   └── sentiment.py     # SentimentIndicators dataclass
├── services/
│   ├── watchlist_service.py  # CRUD operations for watchlist
│   ├── market_data_service.py  # yfinance wrapper with caching
│   ├── gex_calculator.py  # GEX, Max Pain, Walls calculations
│   └── sentiment_service.py  # RSI, PCR, IV percentile calculations
├── database/
│   └── db.py            # SQLite connection and schema management
└── ui/
    ├── sidebar.py       # Watchlist management UI
    ├── scanner_view.py  # Scanner table component
    └── deep_dive_view.py  # Detailed analysis component

tests/
├── unit/
│   ├── test_gex_calculator.py  # GEX calculation tests
│   ├── test_sentiment_service.py  # Sentiment calculation tests
│   └── test_watchlist_service.py  # Watchlist CRUD tests
├── integration/
│   ├── test_market_data_api.py  # yfinance contract tests
│   └── test_database.py  # SQLite integration tests
└── contract/
    └── test_yfinance_schema.py  # Options chain schema validation

# Database
trading_journal.db       # SQLite database (excluded from git)

# Configuration
.env                     # API keys (excluded from git)
.env.example             # Template for required env vars
```

**Structure Decision**: Single Streamlit application with modular separation of concerns. Streamlit's multi-page app structure (`pages/` directory) fits the existing multi-module architecture (A-F modules mentioned in user context). Module G (GEX Sentinel) follows the same pattern.

**Rationale**:
- Streamlit enforces single-project structure (no separate frontend/backend)
- `src/` directory groups business logic separate from UI (`pages/`)
- Clear separation: models (data), services (logic), database (persistence), ui (components)
- Tests mirror source structure for easy navigation

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations detected. All constitution principles satisfied.*

---

## Phase 0: Research (Next Step)

Pending research areas:
1. GEX proxy algorithm implementation approaches
2. yfinance options chain API schema and reliability
3. Streamlit caching best practices (@st.cache_data vs @st.cache_resource)
4. SQLite schema design for watchlist + future extensibility
5. Batch processing patterns in Streamlit (progress bar integration)

Output: `research.md` with decisions and rationale for each area.
