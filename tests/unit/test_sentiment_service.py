"""
Unit tests for sentiment service.

TDD workflow: Tests written FIRST per Constitution Principle V.
Tests validate RSI, PCR, and IV percentile calculations per FR-013, FR-021.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime


def test_calculate_sentiment_indicators_success():
    """
    Test T038: calculate_sentiment_indicators() returns SentimentIndicators.

    Given valid market data,
    When calculate_sentiment_indicators is called,
    Then it returns RSI, PCR, and IV percentile.
    """
    from src.services.sentiment_service import calculate_sentiment_indicators

    with patch('src.services.sentiment_service.fetch_options_chain') as mock_chain, \
         patch('yfinance.Ticker') as mock_ticker:

        # Mock options chain for PCR calculation
        mock_calls = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [1000, 1500, 800],
            'impliedVolatility': [0.25, 0.28, 0.30]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0, 105.0, 110.0],
            'openInterest': [800, 1200, 900],  # Total: 2900
            'impliedVolatility': [0.26, 0.29, 0.31]
        })

        mock_options = MagicMock()
        mock_options.calls = mock_calls
        mock_options.puts = mock_puts
        mock_chain.return_value = mock_options

        # Mock historical price data for RSI
        mock_hist = pd.DataFrame({
            'Close': [100 + i for i in range(20)]  # Uptrend
        })
        mock_ticker.return_value.history.return_value = mock_hist

        # Mock IV history for percentile
        mock_iv_hist = pd.Series([0.20 + i*0.01 for i in range(52)])  # 52 weeks
        with patch('src.services.sentiment_service._fetch_iv_history', return_value=mock_iv_hist):

            result = calculate_sentiment_indicators("NVDA")

            assert result.symbol == "NVDA"
            assert 0 <= result.rsi <= 100, "RSI should be in [0, 100] range"
            assert result.pcr > 0, "PCR should be positive"
            assert 0 <= result.iv_percentile <= 100, "IV percentile should be in [0, 100] range"
            assert isinstance(result.timestamp, datetime)


def test_calculate_pcr_cap_at_10():
    """
    Test T038: PCR is capped at 10.0 if calls approach zero.

    Given minimal call OI,
    When PCR is calculated,
    Then it should be capped at 10.0 (not infinity).
    """
    from src.services.sentiment_service import calculate_sentiment_indicators

    with patch('src.services.sentiment_service.fetch_options_chain') as mock_chain, \
         patch('yfinance.Ticker') as mock_ticker:

        # Mock options chain with very low call OI
        mock_calls = pd.DataFrame({
            'strike': [100.0],
            'openInterest': [10],  # Very low
            'impliedVolatility': [0.25]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0],
            'openInterest': [5000],  # High put OI
            'impliedVolatility': [0.26]
        })

        mock_options = MagicMock()
        mock_options.calls = mock_calls
        mock_options.puts = mock_puts
        mock_chain.return_value = mock_options

        # Mock historical data
        mock_hist = pd.DataFrame({
            'Close': [100 + i for i in range(20)]
        })
        mock_ticker.return_value.history.return_value = mock_hist

        mock_iv_hist = pd.Series([0.20 + i*0.01 for i in range(52)])
        with patch('src.services.sentiment_service._fetch_iv_history', return_value=mock_iv_hist):

            result = calculate_sentiment_indicators("NVDA")

            assert result.pcr <= 10.0, "PCR should be capped at 10.0"


def test_calculate_rsi_insufficient_data():
    """
    Test T038: RSI raises ValueError with insufficient price history.

    Given less than 14 days of price data,
    When calculate_sentiment_indicators is called,
    Then it should raise ValueError.
    """
    from src.services.sentiment_service import calculate_sentiment_indicators
    import streamlit as st

    # Clear cache to ensure fresh test
    st.cache_data.clear()

    with patch('src.services.sentiment_service.fetch_options_chain') as mock_chain, \
         patch('yfinance.Ticker') as mock_ticker:

        # Mock options chain
        mock_calls = pd.DataFrame({
            'strike': [100.0],
            'openInterest': [1000],
            'impliedVolatility': [0.25]
        })

        mock_puts = pd.DataFrame({
            'strike': [100.0],
            'openInterest': [800],
            'impliedVolatility': [0.26]
        })

        mock_options = MagicMock()
        mock_options.calls = mock_calls
        mock_options.puts = mock_puts
        mock_chain.return_value = mock_options

        # Mock insufficient historical data (<14 days)
        mock_hist = pd.DataFrame({
            'Close': [100 + i for i in range(10)]  # Only 10 days
        })
        mock_ticker.return_value.history.return_value = mock_hist

        with pytest.raises(ValueError, match="RSI 計算數據不足"):
            calculate_sentiment_indicators("NVDA_INSUFFICIENT")
