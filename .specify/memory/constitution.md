<!--
SYNC IMPACT REPORT
==================
Version Change: [Initial Template] → 1.0.0
Modified Principles: N/A (Initial ratification)
Added Sections:
  - Core Principles (5 principles defined)
  - Security & Privacy Requirements
  - Performance & Reliability Standards
  - Governance
Removed Sections: N/A
Templates Status:
  ✅ .specify/templates/plan-template.md (aligned with constitution principles)
  ✅ .specify/templates/spec-template.md (aligned with user story requirements)
  ✅ .specify/templates/tasks-template.md (aligned with testing and task structure)
Follow-up TODOs: None
-->

# AI Trading Coach & GEX Sentinel Constitution

## Core Principles

### I. Privacy-First Architecture

All user data MUST remain on the local machine. This is NON-NEGOTIABLE.

- Trade history, watchlists, and analysis results SHALL be stored in local SQLite database
- No data SHALL be transmitted to external services except for:
  - Market data fetching from public APIs (yfinance, IBKR)
  - Optional AI analysis calls to user-configured LLM endpoints
- API keys and credentials MUST be stored in environment variables via `.env` file
- `.gitignore` MUST exclude `.env`, database files, and any cached market data

**Rationale**: Users trust the system with sensitive financial data. Local-first architecture ensures privacy, compliance, and user control.

### II. User-Controlled Monitoring

Users have complete ownership of what they monitor. System reactivity follows user intent.

- Watchlist management MUST be exposed in Streamlit sidebar with add/remove functionality
- System SHALL NOT auto-add or auto-remove symbols without explicit user action
- Monitoring scope is strictly limited to user-defined watchlist
- Each watchlist entry SHALL persist between sessions in local database

**Rationale**: Trading decisions are personal. The system is a tool, not an autonomous agent. Users must maintain full control over what is tracked and analyzed.

### III. Performance Through Aggressive Caching (CRITICAL)

The system MUST remain responsive despite intensive options chain processing.

- ALL market data fetches MUST be wrapped with `@st.cache_data(ttl=300)`
- TTL (Time-To-Live) of 300 seconds (5 minutes) is the default for real-time data
- Batch processing MUST display progress indicators (Streamlit progress bars)
- Long-running operations (>2 seconds) MUST NOT block the UI thread
- GEX calculations SHALL use proxy algorithms (approximation > precision for speed)

**Rationale**: Fetching options chains for multiple symbols is I/O intensive. Without strict caching and async patterns, the UI becomes unusable. 300-second TTL balances data freshness with performance.

### IV. Volatility & Structure First

Price monitoring alone is insufficient. Market structure drives alpha.

- System SHALL compute and display for each watchlist symbol:
  - Gamma Exposure (GEX) levels and walls
  - Max Pain price
  - Implied Volatility (IV) percentile
  - Key support/resistance from GEX
- Price changes are secondary context; structure metrics are primary
- Dashboard SHALL prioritize volatility and positioning over simple P&L

**Rationale**: Retail traders often miss the structural forces (options positioning, dealer hedging) that drive intraday moves. This system surfaces those hidden mechanics.

### V. Test-First for Financial Logic (NON-NEGOTIABLE)

Financial calculations are mission-critical. Bugs cost real money.

- Core logic (GEX calculations, Max Pain, P&L) MUST be unit tested
- TDD workflow: Write test → User approval → Test fails → Implement → Test passes
- Edge cases (missing data, chain fetch failures) MUST be covered
- Integration tests for yfinance API calls MUST validate contract stability
- Manual testing alone is INSUFFICIENT for financial algorithms

**Rationale**: A miscalculation in GEX or Max Pain can lead to incorrect trading decisions. Automated tests ensure correctness and prevent regressions.

## Security & Privacy Requirements

- **SEC-001**: API keys (IBKR, LLM endpoints) MUST be loaded from environment variables only
- **SEC-002**: `.env` file MUST be listed in `.gitignore` to prevent accidental commit
- **SEC-003**: Database file (SQLite) MUST be excluded from version control
- **SEC-004**: No user data SHALL be logged to console or file unless explicitly for debugging (and then sanitized)
- **SEC-005**: Connection to external APIs (yfinance, IBKR) MUST implement retry with exponential backoff and circuit breaker patterns

## Performance & Reliability Standards

- **PERF-001**: Dashboard initial load time MUST be < 3 seconds for watchlists with ≤20 symbols
- **PERF-002**: GEX calculation per symbol MUST complete in < 2 seconds (via caching or approximation)
- **PERF-003**: Batch operations (fetching multiple symbols) MUST display progress indicators
- **PERF-004**: System MUST gracefully handle API rate limits (yfinance, IBKR) with retry logic
- **PERF-005**: Cache TTL SHALL be configurable per data type (default: 300s for real-time, 3600s for historical)
- **PERF-006**: System SHALL operate offline for previously cached data (degraded mode)

## Governance

This constitution supersedes all other project practices. Amendments require:

1. Documented justification of why the change is necessary
2. Approval from project maintainer (ben)
3. Migration plan if existing code violates new principle
4. Update of all dependent templates (plan, spec, tasks) to reflect changes

**Compliance Requirements**:

- All code reviews MUST verify adherence to principles I-V
- Any violation (e.g., blocking I/O, non-cached API calls, hardcoded credentials) MUST be rejected or explicitly justified in `Complexity Tracking` section of plan.md
- Before merging, reviewer SHALL confirm:
  - ✅ User data stays local (Principle I)
  - ✅ User controls what's monitored (Principle II)
  - ✅ Caching applied to data fetches (Principle III)
  - ✅ GEX/volatility metrics present (Principle IV)
  - ✅ Financial logic has tests (Principle V)

**Amendment Process**:

- Propose changes via pull request to this file
- Increment `CONSTITUTION_VERSION` per semantic versioning rules (see below)
- Update `LAST_AMENDED_DATE` to amendment date
- Re-run `/speckit.constitution` command to propagate changes to templates

**Versioning Policy**:

- **MAJOR** (X.0.0): Backward-incompatible changes (e.g., removing a principle, changing "MUST" to "MAY")
- **MINOR** (0.X.0): Adding new principles or expanding guidance
- **PATCH** (0.0.X): Clarifications, typo fixes, non-semantic refinements

**Version**: 1.0.0 | **Ratified**: 2025-11-20 | **Last Amended**: 2025-11-20
