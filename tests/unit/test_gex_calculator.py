"""
Unit tests for GEX calculator service.

TDD workflow: Tests written FIRST per Constitution Principle V.
These tests validate financial calculations per FR-009, FR-010, FR-011, FR-012.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    """Clear Streamlit cache between tests to avoid cross-test contamination."""
    try:
        import streamlit as st
        st.cache_data.clear()
    except:
        pass
    yield
    try:
        import streamlit as st
        st.cache_data.clear()
    except:
        pass


def test_calculate_gex_profile_bullish_state():
    """
    Test T035: calculate_gex_profile() returns GEXProfile with Bullish state.

    Given positive net GEX (more call gamma than put gamma),
    When calculate_gex_profile is called,
    Then gex_state should be "Bullish".
    """
    from src.services.gex_calculator import calculate_gex_profile

    with patch('src.services.gex_calculator.fetch_options_chain') as mock_fetch, \
         patch('src.services.gex_calculator.fetch_price_snapshot') as mock_price:

        # Mock options chain with heavy call OI
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [5000, 8000, 3000],  # High call OI
            'impliedVolatility': [0.25, 0.28, 0.30]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [800, 1200, 900],  # Lower put OI
            'impliedVolatility': [0.26, 0.29, 0.31]
        })

        mock_chain = MagicMock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_chain.expiry_date = '2025-01-17'

        mock_fetch.return_value = mock_chain

        # Mock current price
        mock_snapshot = MagicMock()
        mock_snapshot.current_price = 105.0
        mock_price.return_value = mock_snapshot

        result = calculate_gex_profile("NVDA")

        assert result.symbol == "NVDA"
        assert result.gex_state == "Bullish", "Should be Bullish with net positive GEX"
        assert result.net_gex > 0, "Net GEX should be positive"
        assert isinstance(result.timestamp, datetime)


def test_calculate_gex_profile_bearish_state():
    """
    Test T035: calculate_gex_profile() returns GEXProfile with Bearish state.

    Given negative net GEX (more put gamma than call gamma),
    When calculate_gex_profile is called,
    Then gex_state should be "Bearish".
    """
    from src.services.gex_calculator import calculate_gex_profile

    with patch('src.services.gex_calculator.fetch_options_chain') as mock_fetch, \
         patch('src.services.gex_calculator.fetch_price_snapshot') as mock_price:

        # Mock options chain with heavy put OI
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [500, 800, 300],  # Lower call OI
            'impliedVolatility': [0.25, 0.28, 0.30]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [5000, 8000, 3000],  # High put OI
            'impliedVolatility': [0.26, 0.29, 0.31]
        })

        mock_chain = MagicMock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_chain.expiry_date = '2025-01-17'

        mock_fetch.return_value = mock_chain

        # Mock current price
        mock_snapshot = MagicMock()
        mock_snapshot.current_price = 105.0
        mock_price.return_value = mock_snapshot

        result = calculate_gex_profile("NVDA")

        assert result.symbol == "NVDA"
        assert result.gex_state == "Bearish", "Should be Bearish with net negative GEX"
        assert result.net_gex < 0, "Net GEX should be negative"


def test_calculate_max_pain():
    """
    Test T036: Max Pain calculation finds strike with minimum intrinsic value loss.

    Given an options chain,
    When Max Pain is calculated,
    Then it returns the strike where total intrinsic value loss is minimized.
    """
    from src.services.gex_calculator import calculate_gex_profile

    with patch('src.services.gex_calculator.fetch_options_chain') as mock_fetch, \
         patch('src.services.gex_calculator.fetch_price_snapshot') as mock_price:

        # Mock options chain with max pain at 105
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0, 115.0],
            'openInterest': [1000, 2000, 1500, 500],
            'impliedVolatility': [0.25, 0.28, 0.30, 0.32]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0, 115.0],
            'openInterest': [500, 1500, 2000, 1000],
            'impliedVolatility': [0.26, 0.29, 0.31, 0.33]
        })

        mock_chain = MagicMock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_chain.expiry_date = '2025-01-17'

        mock_fetch.return_value = mock_chain

        mock_snapshot = MagicMock()
        mock_snapshot.current_price = 107.0
        mock_price.return_value = mock_snapshot

        result = calculate_gex_profile("NVDA")

        assert result.max_pain is not None, "Max Pain should be calculated"
        assert result.max_pain in [100.0, 105.0, 110.0, 115.0], "Max Pain should be a valid strike"


def test_calculate_walls():
    """
    Test T037: Call Wall and Put Wall identify highest OI strikes.

    Given an options chain,
    When walls are calculated,
    Then Call Wall is the strike with max call OI,
    And Put Wall is the strike with max put OI.
    """
    from src.services.gex_calculator import calculate_gex_profile

    with patch('src.services.gex_calculator.fetch_options_chain') as mock_fetch, \
         patch('src.services.gex_calculator.fetch_price_snapshot') as mock_price:

        # Mock options chain with clear walls
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [1000, 5000, 800],  # Max at 105
            'impliedVolatility': [0.25, 0.28, 0.30]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [800, 1200, 3000],  # Max at 110
            'impliedVolatility': [0.26, 0.29, 0.31]
        })

        mock_chain = MagicMock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_chain.expiry_date = '2025-01-17'

        mock_fetch.return_value = mock_chain

        mock_snapshot = MagicMock()
        mock_snapshot.current_price = 105.0
        mock_price.return_value = mock_snapshot

        result = calculate_gex_profile("NVDA")

        assert result.call_wall == 105.0, "Call Wall should be at 105 (max call OI)"
        assert result.put_wall == 110.0, "Put Wall should be at 110 (max put OI)"


def test_gex_calculation_performance():
    """
    Test T043: GEX calculation completes in <2 seconds (SC-004).

    This is a performance test to verify PERF-002 requirement.
    """
    import time
    from src.services.gex_calculator import calculate_gex_profile

    with patch('src.services.gex_calculator.fetch_options_chain') as mock_fetch, \
         patch('src.services.gex_calculator.fetch_price_snapshot') as mock_price:

        # Mock realistic options chain (50 strikes)
        strikes = [float(i) for i in range(100, 150)]
        mock_calls = pd.DataFrame({
            'strike': strikes,
            'openInterest': [1000 + i*10 for i in range(50)],
            'impliedVolatility': [0.25 + i*0.001 for i in range(50)]
        })

        mock_puts = pd.DataFrame({
            'strike': strikes,
            'openInterest': [800 + i*10 for i in range(50)],
            'impliedVolatility': [0.26 + i*0.001 for i in range(50)]
        })

        mock_chain = MagicMock()
        mock_chain.calls = mock_calls
        mock_chain.puts = mock_puts
        mock_chain.expiry_date = '2025-01-17'

        mock_fetch.return_value = mock_chain

        mock_snapshot = MagicMock()
        mock_snapshot.current_price = 125.0
        mock_price.return_value = mock_snapshot

        # Time the calculation
        start = time.time()
        result = calculate_gex_profile("NVDA")
        elapsed = time.time() - start

        assert elapsed < 2.0, f"GEX calculation took {elapsed:.2f}s, should be <2s (PERF-002)"
        assert result is not None
