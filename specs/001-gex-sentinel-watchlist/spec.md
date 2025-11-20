# Feature Specification: GEX Sentinel Watchlist Dashboard

**Feature Branch**: `001-gex-sentinel-watchlist`
**Created**: 2025-11-20
**Status**: Draft
**Input**: User description: "AI Trading Coach System - GEX Sentinel Watchlist Dashboard: User-managed watchlist with batch GEX/Max Pain calculations, scanner table, and deep-dive structure analysis"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Watchlist Management (Priority: P1) 🎯 MVP

A trader wants to create and maintain a personalized list of stock symbols to monitor for market structure changes, without being overwhelmed by analyzing every possible ticker in the market.

**Why this priority**: This is the foundation of the entire feature. Without the ability to add/remove symbols, the monitoring system has nothing to track. This delivers immediate value by giving users control over their monitoring scope.

**Independent Test**: User can add symbols (e.g., "NVDA", "AMD") via sidebar input, see them persist in the watchlist display, remove individual symbols via X button, and verify changes persist across page refreshes.

**Acceptance Scenarios**:

1. **Given** the GEX Sentinel page is open, **When** user enters "NVDA" in the sidebar symbol input and clicks "Add to Watchlist", **Then** "NVDA" appears in the watchlist display below the input
2. **Given** "NVDA" is in the watchlist, **When** user refreshes the browser page, **Then** "NVDA" still appears in the watchlist (data persisted)
3. **Given** the watchlist contains ["NVDA", "AMD", "TSLA"], **When** user clicks the X button next to "AMD", **Then** "AMD" is removed and only ["NVDA", "TSLA"] remain
4. **Given** user tries to add "INVALID123" (non-existent symbol), **When** system validates the symbol, **Then** user sees an error message and the symbol is not added
5. **Given** user tries to add "NVDA" when it already exists in watchlist, **When** user clicks "Add to Watchlist", **Then** system shows "Already in watchlist" message and does not create duplicate

---

### User Story 2 - Scanner Table View (Priority: P2)

A trader opens the GEX Sentinel dashboard and immediately sees a high-level summary of all watched stocks, including current price, change percentage, GEX state (trend/volatile), Max Pain distance, and key resistance/support walls, allowing them to quickly identify which symbols need deeper investigation.

**Why this priority**: This is the primary interface for monitoring multiple symbols. It delivers the "at-a-glance" value proposition of the feature. Without this, users would have to check each symbol individually, defeating the purpose of a watchlist.

**Independent Test**: Add 3-5 symbols to watchlist, verify that the scanner table displays all symbols with: price (color-coded), change %, GEX state badge, Max Pain distance, and Call/Put walls. Verify data refreshes within 5 minutes (TTL).

**Acceptance Scenarios**:

1. **Given** watchlist contains ["NVDA", "AMD", "TSLA"], **When** page loads the scanner view, **Then** all three symbols appear as rows in the table
2. **Given** NVDA's current price is higher than previous close, **When** scanner table renders, **Then** NVDA's price is displayed in green with positive change percentage
3. **Given** AMD has negative net GEX, **When** scanner calculates GEX state, **Then** AMD shows "Volatile 🐻" badge
4. **Given** TSLA's Max Pain is $250 and current price is $255, **When** scanner displays Max Pain, **Then** shows "$250 (+2%)" indicating distance and direction
5. **Given** a symbol has highest Call OI at $280 and Put OI at $260, **When** scanner displays walls, **Then** shows "Call Wall: $280 / Put Wall: $260"
6. **Given** watchlist has 10 symbols, **When** batch data fetch runs, **Then** progress bar displays "Analyzing [SYMBOL] (X/10)..." during fetch
7. **Given** cached data for a symbol is less than 5 minutes old, **When** scanner loads, **Then** data loads instantly from cache without refetch

---

### User Story 3 - Deep Dive Structure Analysis (Priority: P3)

After identifying an interesting symbol in the scanner table, a trader selects it to view detailed market structure analysis including visual representation of GEX walls, sentiment indicators (RSI, PCR), and an AI-generated analysis of the structural setup.

**Why this priority**: This provides the actionable intelligence layer on top of the scanner. While the scanner identifies "what" is happening, the deep dive explains "why" and "what it means", enabling informed trading decisions.

**Independent Test**: Select a symbol from scanner table (or dropdown), verify detailed view displays structure card (Net GEX, trend/range status), walls card (Call Wall, Max Pain, Put Wall visualization), sentiment card (RSI gauge, PCR ratio), and AI analysis button that generates structure interpretation.

**Acceptance Scenarios**:

1. **Given** scanner table is displayed, **When** user clicks on the "NVDA" row, **Then** page transitions to deep dive view showing NVDA's detailed structure
2. **Given** deep dive view is open for NVDA, **When** structure card loads, **Then** displays Net GEX value (e.g., "+$2.5B") and status badge ("Trending 🐂" or "Ranging")
3. **Given** NVDA has Call Wall at $580, Max Pain at $550, Put Wall at $520, **When** walls card renders, **Then** displays visual list with Max Pain in center and walls above/below
4. **Given** deep dive view is open, **When** sentiment card loads, **Then** displays RSI gauge (0-100 scale with current value) and PCR ratio (e.g., "0.85")
5. **Given** user is viewing NVDA deep dive, **When** user clicks "🤖 Analyze Structure" button, **Then** AI analysis appears with interpretation of GEX state, walls, and price action context
6. **Given** AI analysis is generated for NVDA, **When** analysis completes, **Then** displays text analysis referencing NVDA's specific GEX levels, walls, and sentiment indicators

---

### User Story 4 - Watchlist Categorization (Optional: P4)

A trader wants to organize their watchlist into categories (e.g., "Tech", "Core Holdings", "Speculative") to better manage different segments of their monitoring universe.

**Why this priority**: This is a quality-of-life enhancement that becomes valuable when users have large watchlists (10+ symbols). It's not essential for core functionality but improves organization at scale.

**Independent Test**: Add symbols with category labels, verify scanner table can be filtered or grouped by category, verify categories persist across sessions.

**Acceptance Scenarios**:

1. **Given** user adds "NVDA" to watchlist, **When** adding the symbol, **Then** user can optionally select a category from dropdown (e.g., "Tech", "Core", "Speculative") or leave blank
2. **Given** watchlist contains symbols with mixed categories, **When** scanner table loads, **Then** symbols can be filtered by category via dropdown selector
3. **Given** user has categorized their watchlist, **When** viewing scanner table, **Then** symbols are grouped by category with category headers

---

### Edge Cases

- **What happens when a symbol is delisted or ticker changes?** System should detect invalid symbols during fetch and display error state in scanner row, allowing user to remove or update the symbol.
- **What happens when options chain data is unavailable (illiquid stock)?** System should gracefully handle missing data by displaying "N/A" for GEX/Max Pain fields and showing a warning icon with tooltip explaining data unavailability.
- **What happens when API rate limit is hit during batch fetch?** System should pause fetching, display rate limit message, and resume after cooldown period. Already-fetched symbols should remain visible.
- **What happens when user has 50+ symbols in watchlist?** System should maintain performance via caching and batch processing, but may need pagination or virtual scrolling for scanner table.
- **What happens when market is closed?** System should display last available data with timestamp indicating staleness (e.g., "Data as of 4:00 PM ET") and disable real-time refresh.
- **What happens when user's watchlist is empty?** Display onboarding message: "Your watchlist is empty. Add symbols above to start monitoring market structure."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to add stock symbols (tickers) to a persistent watchlist via text input
- **FR-002**: System MUST validate entered symbols before adding to watchlist (reject invalid tickers)
- **FR-003**: System MUST prevent duplicate symbols from being added to the same watchlist
- **FR-004**: System MUST allow users to remove individual symbols from their watchlist
- **FR-005**: System MUST persist watchlist data between sessions (database storage)
- **FR-006**: System MUST fetch current price and previous close for each watchlist symbol
- **FR-007**: System MUST calculate price change percentage for each symbol
- **FR-008**: System MUST fetch options chain data for each watchlist symbol
- **FR-009**: System MUST calculate Gamma Exposure (GEX) for each symbol using proxy algorithm
- **FR-010**: System MUST determine GEX state (Bullish/Trending or Bearish/Volatile) based on net GEX sign
- **FR-011**: System MUST calculate Max Pain strike price (strike with minimum total intrinsic value)
- **FR-012**: System MUST identify Call Wall (highest call open interest strike) and Put Wall (highest put open interest strike)
- **FR-013**: System MUST calculate Implied Volatility percentile for each symbol using 52-week (1 year) lookback period
- **FR-014**: System MUST display scanner table with all watchlist symbols showing: ticker, price, change %, GEX state, Max Pain distance, Call/Put walls
- **FR-015**: System MUST color-code price changes (green for positive, red for negative)
- **FR-016**: System MUST display progress indicator during batch data fetching for multiple symbols
- **FR-017**: System MUST cache fetched data with 5-minute TTL to avoid redundant API calls
- **FR-018**: Users MUST be able to select a symbol from scanner table to view detailed analysis
- **FR-019**: System MUST display deep dive view with structure card (Net GEX value, trending/ranging status)
- **FR-020**: System MUST display walls visualization showing Call Wall, Max Pain, and Put Wall positions
- **FR-021**: System MUST display sentiment indicators including RSI gauge and Put/Call ratio (PCR)
- **FR-022**: System MUST provide AI analysis capability that generates structure interpretation for selected symbol
- **FR-023**: AI analysis MUST reference the specific symbol's GEX levels, walls, price action, and sentiment data
- **FR-024**: System MUST handle API failures gracefully with retry logic and user-visible error states
- **FR-025**: System MUST complete GEX calculation per symbol in under 2 seconds (via approximation algorithm)

### Key Entities

- **Watchlist Entry**: A user-tracked stock symbol with metadata (symbol ticker, date added, optional category). Represents the user's monitoring list.
- **GEX Profile**: Calculated market structure snapshot for a symbol including Net GEX, GEX state (bullish/bearish), Call Wall strike, Put Wall strike, Max Pain price. Derived from options chain data.
- **Market Snapshot**: Current price, previous close, change percentage, timestamp for a symbol. Provides price context for structure analysis.
- **Sentiment Indicators**: RSI value (0-100), Put/Call Ratio (PCR), IV percentile for a symbol. Provides momentum and positioning context.
- **Options Chain**: Raw options data (strikes, open interest, implied volatility) fetched from market data provider. Foundation for all GEX calculations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can add a new symbol to watchlist and see it appear in under 3 seconds
- **SC-002**: Scanner table displays all watchlist symbols (up to 20) with complete data in under 10 seconds on initial load
- **SC-003**: Subsequent scanner refreshes with cached data complete in under 1 second
- **SC-004**: GEX calculation completes for each symbol in under 2 seconds
- **SC-005**: Users can transition from scanner view to deep dive view in under 1 second
- **SC-006**: AI structure analysis generates in under 5 seconds for a single symbol
- **SC-007**: 95% of watchlist management operations (add/remove) succeed without errors
- **SC-008**: System handles watchlists with 20+ symbols without UI blocking or freezing
- **SC-009**: Progress indicators display for any batch operation taking longer than 2 seconds
- **SC-010**: Watchlist data persists correctly across 100% of browser sessions (no data loss)
- **SC-011**: Users can identify highest-priority symbols for analysis within 30 seconds of opening dashboard
- **SC-012**: 90% of users successfully add their first symbol and view scanner data on first attempt (onboarding success)

### Assumptions

- **Market data API** (yfinance or equivalent) provides reliable options chain data with strike-level open interest
- **Symbol validation** can be performed via market data API query (invalid symbols return empty results)
- **GEX proxy algorithm** is sufficient approximation - exact dealer positioning calculations are not required
- **5-minute cache TTL** balances data freshness with performance for intraday monitoring
- **IV percentile** uses 52-week lookback period (industry standard for long-term context)
- **RSI period** assumes standard 14-period calculation
- **Max Pain** calculation assumes all options expire worthless except intrinsic value (standard definition)
- **Streaming quotes** are not required - 5-minute delayed data via cache refresh is acceptable
- **Concurrent users** limited to single user (local deployment) - no multi-user session management needed
- **Watchlist size** expected to be 5-30 symbols for typical user (optimized for this range)
- **AI analysis** uses user-configured LLM endpoint (API key in environment variables)
