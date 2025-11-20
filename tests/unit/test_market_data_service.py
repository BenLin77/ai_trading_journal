"""
Unit tests for market data service.

TDD workflow: Tests written FIRST per Constitution Principle V.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime


def test_fetch_options_chain_success():
    """
    Test T031: fetch_options_chain() returns OptionsChain with calls and puts.

    Given a valid symbol,
    When fetch_options_chain is called,
    Then it returns OptionsChain with DataFrames for calls and puts.
    """
    from src.services.market_data_service import fetch_options_chain

    with patch('yfinance.Ticker') as mock_ticker:
        # Mock options chain data
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [1000, 1500, 800],
            'impliedVolatility': [0.25, 0.28, 0.30],
            'lastPrice': [5.0, 3.0, 1.5]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [800, 1200, 900],
            'impliedVolatility': [0.26, 0.29, 0.31],
            'lastPrice': [4.0, 2.5, 1.0]
        })

        mock_option_chain = MagicMock()
        mock_option_chain.calls = mock_calls
        mock_option_chain.puts = mock_puts

        mock_ticker.return_value.options = ['2025-01-17', '2025-02-21']
        mock_ticker.return_value.option_chain.return_value = mock_option_chain

        result = fetch_options_chain("NVDA")

        assert result is not None, "Should return OptionsChain"
        assert hasattr(result, 'calls'), "Should have calls DataFrame"
        assert hasattr(result, 'puts'), "Should have puts DataFrame"
        assert len(result.calls) > 0, "Calls should not be empty"
        assert len(result.puts) > 0, "Puts should not be empty"


def test_fetch_options_chain_no_options_available():
    """
    Test T031: fetch_options_chain() raises ValueError for illiquid stock.

    Given a symbol with no options,
    When fetch_options_chain is called,
    Then it raises ValueError.
    """
    from src.services.market_data_service import fetch_options_chain

    with patch('yfinance.Ticker') as mock_ticker:
        # Mock no options available
        mock_ticker.return_value.options = []

        with pytest.raises(ValueError, match="No options available"):
            fetch_options_chain("ILLIQUID")


def test_fetch_price_snapshot_success():
    """
    Test T032: fetch_price_snapshot() returns MarketSnapshot with price data.

    Given a valid symbol,
    When fetch_price_snapshot is called,
    Then it returns MarketSnapshot with current price and change %.
    """
    from src.services.market_data_service import fetch_price_snapshot

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {
            'regularMarketPrice': 500.0,
            'previousClose': 490.0,
            'symbol': 'NVDA'
        }

        result = fetch_price_snapshot("NVDA")

        assert result.symbol == "NVDA"
        assert result.current_price == 500.0
        assert result.previous_close == 490.0
        assert abs(result.change_pct - 2.04) < 0.01  # (500-490)/490 * 100
        assert isinstance(result.timestamp, datetime)


def test_fetch_price_snapshot_invalid_symbol():
    """
    Test T032: fetch_price_snapshot() raises ValueError for invalid symbol.
    """
    from src.services.market_data_service import fetch_price_snapshot

    with patch('yfinance.Ticker') as mock_ticker:
        mock_ticker.return_value.info = {}

        with pytest.raises(ValueError, match="No price data"):
            fetch_price_snapshot("INVALID")
