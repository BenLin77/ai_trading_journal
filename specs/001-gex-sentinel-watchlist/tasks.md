# Tasks: GEX Sentinel Watchlist Dashboard

**Input**: Design documents from `/specs/001-gex-sentinel-watchlist/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD workflow enforced per Constitution Principle V (NON-NEGOTIABLE). All financial calculation tests written BEFORE implementation.

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below use single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Initialize Python project with uv package manager (run: uv init)
- [X] T002 [P] Add core dependencies via uv (streamlit pandas numpy yfinance plotly python-dotenv py-vollib scipy)
- [X] T003 [P] Add testing dependencies via uv --dev (pytest pytest-mock pytest-cov)
- [X] T004 Create .env.example file with LLM_API_KEY, LLM_API_ENDPOINT, DB_PATH template variables
- [X] T005 [P] Verify .gitignore includes .env, *.db, __pycache__, .venv, *.pyc, cache/ per Constitution SEC-002
- [X] T006 Create src/ directory structure (models/, services/, database/, ui/ subdirectories)
- [X] T007 [P] Create tests/ directory structure (unit/, integration/, contract/ subdirectories)
- [X] T008 [P] Create pages/ directory for Streamlit multi-page app
- [X] T009 [P] Add __init__.py files to all Python package directories (src/, src/models/, src/services/, src/database/, src/ui/, tests/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Foundation

- [X] T010 Create database schema SQL in src/database/db.py (watchlist table with id, symbol UNIQUE, added_at, category, notes, enabled columns)
- [X] T011 Implement get_db_connection() with @st.cache_resource decorator in src/database/db.py (WAL mode, row_factory configuration)
- [X] T012 Implement initialize_db() with schema version migration logic in src/database/db.py (PRAGMA user_version check)

### Data Models (Foundational)

- [X] T013 [P] Create WatchlistEntry dataclass in src/models/watchlist.py (id, symbol, added_at, category, notes, enabled fields)
- [X] T014 [P] Create GEXProfile dataclass in src/models/gex_profile.py (symbol, net_gex, gex_state, call_wall, put_wall, max_pain, timestamp)
- [X] T015 [P] Create MarketSnapshot dataclass in src/models/gex_profile.py (symbol, current_price, previous_close, change_pct, timestamp)
- [X] T016 [P] Create SentimentIndicators dataclass in src/models/sentiment.py (symbol, rsi, pcr, iv_percentile, timestamp)

### Integration Tests (Foundation Validation)

- [X] T017 Write integration test for database initialization in tests/integration/test_database.py (verify watchlist table exists, schema correct)
- [X] T018 Write integration test for database persistence in tests/integration/test_database.py (insert/query/delete operations work)
- [X] T019 Write contract test for yfinance schema in tests/contract/test_yfinance_schema.py (verify option_chain returns expected columns)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Watchlist Management (Priority: P1) 🎯 MVP

**Goal**: Users can add/remove symbols via sidebar, with persistence across sessions

**Independent Test**: Add "NVDA" via sidebar → verify in display → refresh page → verify persists → remove "NVDA" → verify gone

### Tests for User Story 1 (TDD - Write FIRST) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T020 [P] [US1] Write unit test for add_symbol() success case in tests/unit/test_watchlist_service.py (valid symbol, returns WatchlistEntry)
- [X] T021 [P] [US1] Write unit test for add_symbol() duplicate rejection in tests/unit/test_watchlist_service.py (IntegrityError on duplicate)
- [X] T022 [P] [US1] Write unit test for add_symbol() invalid symbol rejection in tests/unit/test_watchlist_service.py (ValueError for "INVALID123")
- [X] T023 [P] [US1] Write unit test for remove_symbol() in tests/unit/test_watchlist_service.py (returns True if deleted, False if not found)
- [X] T024 [P] [US1] Write unit test for get_all_symbols() in tests/unit/test_watchlist_service.py (returns list ordered by added_at DESC)

### Implementation for User Story 1

- [X] T025 [US1] Implement add_symbol(symbol, category) in src/services/watchlist_service.py (validate via yfinance, uppercase, insert to DB, return WatchlistEntry)
- [X] T026 [US1] Implement remove_symbol(symbol) in src/services/watchlist_service.py (DELETE from watchlist WHERE symbol=?, return bool)
- [X] T027 [US1] Implement get_all_symbols() in src/services/watchlist_service.py (SELECT * FROM watchlist ORDER BY added_at DESC)
- [X] T028 [US1] Create sidebar watchlist management UI in src/ui/sidebar.py (text input for symbol, "Add to Watchlist" button, display current symbols with X buttons)
- [X] T029 [US1] Wire sidebar UI to watchlist service in pages/6_GEX_Sentinel.py (st.sidebar context, call add_symbol on button click, display get_all_symbols results, handle errors with st.error)
- [X] T030 [US1] Add input validation and error handling in src/ui/sidebar.py (duplicate detection → st.warning, invalid symbol → st.error, success → st.success)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Scanner Table View (Priority: P2)

**Goal**: Display high-level GEX metrics for all watchlist symbols in table format

**Independent Test**: Add 3 symbols → verify scanner table shows price (color-coded), change %, GEX state, Max Pain, walls → verify cache hits on refresh

### Tests for User Story 2 (TDD - Write FIRST) ⚠️

- [ ] T031 [P] [US2] Write unit test for fetch_options_chain() in tests/unit/test_market_data_service.py (returns OptionsChain with calls/puts DataFrames)
- [ ] T032 [P] [US2] Write unit test for fetch_price_snapshot() in tests/unit/test_market_data_service.py (returns MarketSnapshot with change_pct calculated)
- [ ] T033 [P] [US2] Write unit test for calculate_gex_profile() in tests/unit/test_gex_calculator.py (net_gex calculated correctly, gex_state="Bullish" if net_gex>0)
- [ ] T034 [P] [US2] Write unit test for _calculate_gamma() helper in tests/unit/test_gex_calculator.py (Black-Scholes gamma formula correct)
- [ ] T035 [P] [US2] Write unit test for _calculate_max_pain() helper in tests/unit/test_gex_calculator.py (finds strike with min intrinsic loss)
- [ ] T036 [P] [US2] Write unit test for GEX calculation with missing data in tests/unit/test_gex_calculator.py (ValueError if no options chain)
- [ ] T037 [P] [US2] Write unit test for GEX calculation timeout in tests/unit/test_gex_calculator.py (RuntimeError if >2s)

### Implementation for User Story 2

- [ ] T038 [P] [US2] Implement fetch_options_chain(symbol, expiry) with @st.cache_data(ttl=300) in src/services/market_data_service.py (yfinance wrapper, retry logic, return OptionsChain dataclass)
- [ ] T039 [P] [US2] Implement fetch_price_snapshot(symbol) with @st.cache_data(ttl=300) in src/services/market_data_service.py (yfinance Ticker.info, calculate change_pct, return MarketSnapshot)
- [ ] T040 [US2] Implement _calculate_gamma(strike, spot, iv, tte) in src/services/gex_calculator.py (Black-Scholes formula using scipy.stats.norm)
- [ ] T041 [US2] Implement _calculate_max_pain(options_chain) in src/services/gex_calculator.py (iterate strikes, sum intrinsic losses, return min)
- [ ] T042 [US2] Implement calculate_gex_profile(symbol) with @st.cache_data(ttl=300) in src/services/gex_calculator.py (fetch options chain, calculate per-strike GEX, determine net_gex/state/walls/max_pain, return GEXProfile)
- [ ] T043 [US2] Add performance timeout check to calculate_gex_profile() in src/services/gex_calculator.py (raise RuntimeError if >2s per PERF-002)
- [ ] T044 [US2] Implement batch fetching logic with progress bar in src/ui/scanner_view.py (st.progress and st.empty for status text, iterate watchlist symbols, handle errors gracefully)
- [ ] T045 [US2] Create scanner table component in src/ui/scanner_view.py (build DataFrame with Ticker, Price, Change%, GEX State, Max Pain, Call/Put Walls columns, color-code prices)
- [ ] T046 [US2] Wire scanner view to main page in pages/6_GEX_Sentinel.py (fetch all symbols, batch call GEX/price fetchers with progress bar, display st.dataframe with column configuration)
- [ ] T047 [US2] Add empty watchlist onboarding message in pages/6_GEX_Sentinel.py (if watchlist empty, display "Your watchlist is empty. Add symbols above to start monitoring market structure.")
- [ ] T048 [US2] Add error state handling for missing options data in src/ui/scanner_view.py (display "N/A" for GEX fields if ValueError, show warning icon with tooltip)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Deep Dive Structure Analysis (Priority: P3)

**Goal**: Detailed view for selected symbol with GEX walls visualization, sentiment indicators, and AI analysis

**Independent Test**: Select "NVDA" from scanner → verify structure card (Net GEX, state), walls card, sentiment card (RSI, PCR), AI button → click → verify analysis appears

### Tests for User Story 3 (TDD - Write FIRST) ⚠️

- [ ] T049 [P] [US3] Write unit test for calculate_sentiment_indicators() in tests/unit/test_sentiment_service.py (RSI calculation correct for 14-period)
- [ ] T050 [P] [US3] Write unit test for PCR calculation in tests/unit/test_sentiment_service.py (put_OI / call_OI, capped at 10.0)
- [ ] T051 [P] [US3] Write unit test for IV percentile calculation in tests/unit/test_sentiment_service.py (percentile rank of current vs 52-week history)
- [ ] T052 [P] [US3] Write unit test for sentiment with insufficient data in tests/unit/test_sentiment_service.py (ValueError if <14 days for RSI)
- [ ] T053 [P] [US3] Write unit test for generate_structure_analysis() in tests/unit/test_ai_service.py (returns markdown string, calls LLM API with correct prompt)
- [ ] T054 [P] [US3] Write unit test for AI analysis timeout in tests/unit/test_ai_service.py (requests.Timeout if >5s per SC-006)

### Implementation for User Story 3

- [ ] T055 [P] [US3] Implement fetch_iv_history(symbol, period) with @st.cache_data(ttl=3600) in src/services/market_data_service.py (yfinance historical IV data, return pd.Series)
- [ ] T056 [P] [US3] Implement RSI calculation in src/services/sentiment_service.py (14-period Wilder's RSI, handle insufficient data)
- [ ] T057 [US3] Implement calculate_sentiment_indicators(symbol) with @st.cache_data(ttl=300) in src/services/sentiment_service.py (fetch options chain for PCR, fetch IV history for percentile, calculate RSI, return SentimentIndicators)
- [ ] T058 [US3] Implement generate_structure_analysis(symbol, gex_profile, sentiment) in src/services/ai_service.py (load LLM_API_KEY from env, format prompt template, call API with 5s timeout, return markdown text)
- [ ] T059 [US3] Add LLM API error handling in src/services/ai_service.py (ValueError if no API key, requests.Timeout with user message)
- [ ] T060 [US3] Create structure card component in src/ui/deep_dive_view.py (display Net GEX value with B/M suffix, GEX state badge with emoji)
- [ ] T061 [US3] Create walls visualization component in src/ui/deep_dive_view.py (vertical list showing Call Wall, Max Pain (center), Put Wall with plotly or st.metric)
- [ ] T062 [US3] Create sentiment card component in src/ui/deep_dive_view.py (RSI gauge 0-100 with plotly indicator, PCR ratio display)
- [ ] T063 [US3] Add symbol selection mechanism in pages/6_GEX_Sentinel.py (st.selectbox after scanner table or row click handler via st.dataframe selection_mode)
- [ ] T064 [US3] Wire deep dive view to selected symbol in pages/6_GEX_Sentinel.py (fetch GEXProfile and SentimentIndicators from cache, display structure/walls/sentiment cards)
- [ ] T065 [US3] Add "🤖 Analyze Structure" button in pages/6_GEX_Sentinel.py (st.button triggers AI analysis, display loading spinner, show result with st.markdown)
- [ ] T066 [US3] Add view toggle between scanner and deep dive in pages/6_GEX_Sentinel.py (st.session_state to track current view, transition in <1s per SC-005)

**Checkpoint**: All core user stories (P1-P3) should now be independently functional

---

## Phase 6: User Story 4 - Watchlist Categorization (Priority: P4 - OPTIONAL)

**Goal**: Organize watchlist into categories for better management

**Independent Test**: Add "NVDA" with category "Tech" → add "SPY" with category "Core" → verify filter dropdown works → verify categories persist

### Implementation for User Story 4 (OPTIONAL)

- [ ] T067 [P] [US4] Write unit test for get_symbols_by_category() in tests/unit/test_watchlist_service.py (returns filtered list)
- [ ] T068 [US4] Implement get_symbols_by_category(category) in src/services/watchlist_service.py (SELECT * FROM watchlist WHERE category=?)
- [ ] T069 [US4] Add category dropdown to sidebar add form in src/ui/sidebar.py (st.selectbox with ["Tech", "Core", "Speculative", None])
- [ ] T070 [US4] Add category filter to scanner view in src/ui/scanner_view.py (st.selectbox to filter displayed symbols)
- [ ] T071 [US4] Add category grouping headers to scanner table in src/ui/scanner_view.py (st.subheader for each category section if enabled)

**Checkpoint**: Optional categorization feature complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T072 [P] Add cache invalidation "Refresh" button in pages/6_GEX_Sentinel.py (st.button → st.cache_data.clear())
- [ ] T073 [P] Add market closed detection and timestamp display in src/services/market_data_service.py (check market hours, add "Data as of [timestamp]" if stale)
- [ ] T074 [P] Add API rate limit handling and circuit breaker in src/services/market_data_service.py (track consecutive failures, pause with cooldown message)
- [ ] T075 [P] Add pagination or virtual scrolling for large watchlists in src/ui/scanner_view.py (if >30 symbols, use st.dataframe height limit)
- [ ] T076 Add performance logging for GEX calculations in src/services/gex_calculator.py (log warning if >2s, log timing stats)
- [ ] T077 [P] Write README.md quickstart section at repository root (setup instructions, running app, TDD workflow)
- [ ] T078 [P] Create example .env.example file if not exists (LLM_API_KEY, DB_PATH templates)
- [ ] T079 Run complete test suite and verify all tests pass (uv run pytest tests/ --cov=src)
- [ ] T080 Run performance validation tests per quickstart.md (verify SC-001 through SC-006 targets met)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on other stories
  - User Story 3 (P3): Can start after Foundational - Uses GEX/Price data from US2 but independently testable
  - User Story 4 (P4): Can start after Foundational - Optional enhancement
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent - foundation for watchlist
- **User Story 2 (P2)**: Independent - can implement with hardcoded test symbols if US1 not complete
- **User Story 3 (P3)**: Independent - can implement with symbol selection dropdown if US2 scanner not complete
- **User Story 4 (P4)**: Independent - optional enhancement to US1

### TDD Workflow Within Each User Story

**CRITICAL - Constitution Principle V (NON-NEGOTIABLE)**:

1. **Write Tests FIRST** (Tasks with "Write unit test" in description)
2. **Run Tests** → Verify they FAIL (no implementation yet)
3. **Implement Feature** (Tasks with "Implement" in description)
4. **Run Tests** → Verify they PASS
5. **Refactor** if needed, re-run tests

**Example for US2 GEX Calculation**:
```bash
# Step 1: Write test
nano tests/unit/test_gex_calculator.py  # T033

# Step 2: Run test (should FAIL)
uv run pytest tests/unit/test_gex_calculator.py::test_calculate_gex_profile -v

# Step 3: Implement
nano src/services/gex_calculator.py  # T042

# Step 4: Run test (should PASS)
uv run pytest tests/unit/test_gex_calculator.py::test_calculate_gex_profile -v
```

### Parallel Opportunities

**Within Setup Phase (Phase 1)**:
- T002, T003 (dependencies)
- T005, T006, T007, T008, T009 (directory/file creation)

**Within Foundational Phase (Phase 2)**:
- T013, T014, T015, T016 (data models - different files)

**Within User Story Test Writing**:
- All test tasks marked [P] can run in parallel within each story
  - US1: T020-T024 (all test files)
  - US2: T031-T037 (all test files)
  - US3: T049-T054 (all test files)

**Within User Story Implementation**:
- Models within a story (if multiple) can be parallel
- Services can be parallel if no inter-dependencies
- US2: T038, T039 (different services)
- US3: T055, T056 (different services)

**Across User Stories** (after Foundational complete):
- US1, US2, US3, US4 can ALL be worked on in parallel by different developers
- Each story is independently testable and deliverable

---

## Parallel Example: User Story 2 (GEX Scanner)

```bash
# Launch all tests for User Story 2 together (Write FIRST):
# Terminal 1:
uv run pytest tests/unit/test_market_data_service.py -k "fetch_options_chain or fetch_price_snapshot" -v

# Terminal 2:
uv run pytest tests/unit/test_gex_calculator.py -v

# After tests written and FAILING, implement in parallel:
# Developer A:
nano src/services/market_data_service.py  # T038, T039

# Developer B:
nano src/services/gex_calculator.py  # T040, T041, T042, T043

# Developer C:
nano src/ui/scanner_view.py  # T044, T045
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Goal**: Deliver smallest testable increment

1. Complete Phase 1: Setup (T001-T009)
2. Complete Phase 2: Foundational (T010-T019) - BLOCKS all stories
3. Complete Phase 3: User Story 1 (T020-T030)
4. **STOP and VALIDATE**: Test watchlist add/remove, verify persistence
5. Deploy/demo if ready

**MVP Scope**: Users can manage watchlist (add/remove symbols), data persists. No GEX calculations yet.

**Time Estimate**: ~1-2 days for single developer

### Incremental Delivery (Recommended)

**Goal**: Add value incrementally, validate each story independently

1. **Sprint 1**: Setup + Foundational + US1 → **Watchlist Management MVP**
   - Test: Add/remove symbols, verify persistence
   - Deploy: Users can curate watchlist

2. **Sprint 2**: US2 → **Scanner Table with GEX Metrics**
   - Test: Add 5 symbols, verify scanner displays GEX/Max Pain/Walls
   - Deploy: Users can monitor market structure

3. **Sprint 3**: US3 → **Deep Dive Analysis with AI**
   - Test: Select symbol, verify detailed metrics, test AI button
   - Deploy: Users get actionable intelligence

4. **Sprint 4** (Optional): US4 → **Categorization**
   - Test: Add categories, filter, verify persistence
   - Deploy: Enhanced organization for large watchlists

5. **Sprint 5**: Polish → **Production Hardening**
   - Test: Performance validation, edge cases, full test suite
   - Deploy: Production-ready release

### Parallel Team Strategy

With 3 developers after Foundational phase completes:

**Developer A**: User Story 1 (Watchlist Management)
- T020-T030
- Deliverable: Sidebar watchlist CRUD

**Developer B**: User Story 2 (Scanner Table)
- T031-T048
- Deliverable: GEX scanner table

**Developer C**: User Story 3 (Deep Dive)
- T049-T066
- Deliverable: Detailed analysis views

**Integration Point**: Week 2 - merge all stories, verify independence

---

## Notes

- **[P] tasks** = different files, no dependencies, safe to parallelize
- **[Story] label** maps task to specific user story for traceability
- **TDD CRITICAL**: All financial logic tests (T020-T024, T031-T037, T049-T054) MUST be written BEFORE implementation per Constitution Principle V
- Each user story should be independently completable and testable
- Verify tests FAIL before implementing (Red-Green-Refactor cycle)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Constitution Compliance Checklist

Before marking feature complete, verify:

- ✅ **Principle I (Privacy)**: .env in .gitignore (T005), database local-only (T010-T012)
- ✅ **Principle II (User Control)**: Explicit watchlist management (T025-T030), no auto-population
- ✅ **Principle III (Caching)**: All data fetches use @st.cache_data(ttl=300) (T038, T039, T042, T057)
- ✅ **Principle IV (Structure First)**: GEX/Max Pain prominent in scanner (T045), deep dive (T060-T062)
- ✅ **Principle V (Test-First)**: All tests written BEFORE implementation (T020-T024, T031-T037, T049-T054)

Refer to [constitution.md](../../.specify/memory/constitution.md) for full principles.
