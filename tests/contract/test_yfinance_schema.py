"""
Contract test for yfinance options chain schema.

Verifies that yfinance API returns expected columns per research.md Section 2.
"""

import pytest
import yfinance as yf


def test_yfinance_options_chain_schema():
    """
    Test T019: Verify option_chain returns expected columns.

    This test validates the contract with yfinance API to ensure
    our GEX calculations will have required data fields.

    Expected columns per research.md:
    - contractSymbol, strike, lastPrice, bid, ask
    - volume, openInterest, impliedVolatility
    """
    # Use a well-known liquid stock with active options
    ticker = yf.Ticker("SPY")

    # Get available expiration dates
    try:
        expirations = ticker.options
        assert len(expirations) > 0, "SPY should have options expirations"
    except Exception as e:
        pytest.skip(f"Could not fetch options expirations: {e}")

    # Fetch options chain for nearest expiration
    nearest_expiry = expirations[0]

    try:
        option_chain = ticker.option_chain(nearest_expiry)
    except Exception as e:
        pytest.skip(f"Could not fetch options chain: {e}")

    # Verify structure
    assert hasattr(option_chain, 'calls'), "Options chain should have 'calls' attribute"
    assert hasattr(option_chain, 'puts'), "Options chain should have 'puts' attribute"

    # Expected columns per research.md Section 2
    expected_columns = [
        'contractSymbol',
        'strike',
        'lastPrice',
        'bid',
        'ask',
        'volume',
        'openInterest',
        'impliedVolatility'
    ]

    # Verify calls DataFrame
    calls_df = option_chain.calls
    assert len(calls_df) > 0, "Calls DataFrame should not be empty"

    for col in expected_columns:
        assert col in calls_df.columns, f"Calls DataFrame should have '{col}' column"

    # Verify puts DataFrame
    puts_df = option_chain.puts
    assert len(puts_df) > 0, "Puts DataFrame should not be empty"

    for col in expected_columns:
        assert col in puts_df.columns, f"Puts DataFrame should have '{col}' column"

    # Verify data types
    assert calls_df['strike'].dtype in ['float64', 'float32', 'int64'], \
        "Strike should be numeric"
    assert calls_df['openInterest'].dtype in ['int64', 'int32', 'float64'], \
        "Open Interest should be numeric"
    assert calls_df['impliedVolatility'].dtype in ['float64', 'float32'], \
        "Implied Volatility should be float"

    # Verify non-negative constraints
    assert (calls_df['strike'] > 0).all(), "All strikes should be positive"
    assert (calls_df['openInterest'] >= 0).all(), "Open Interest should be non-negative"
    assert (puts_df['openInterest'] >= 0).all(), "Put Open Interest should be non-negative"


def test_yfinance_ticker_validation():
    """
    Test that yfinance can validate invalid symbols.

    This is used in watchlist_service.add_symbol() validation.
    """
    # Valid ticker
    valid_ticker = yf.Ticker("AAPL")
    info = valid_ticker.info
    assert info is not None, "Valid ticker should return info"
    assert 'symbol' in info or 'shortName' in info, "Info should contain symbol data"

    # Invalid ticker should return empty or minimal info
    invalid_ticker = yf.Ticker("INVALID12345XYZ")
    invalid_info = invalid_ticker.info

    # yfinance may return empty dict or dict with regularMarketPrice = None
    # Either indicates invalid symbol
    is_invalid = (
        len(invalid_info) == 0 or
        invalid_info.get('regularMarketPrice') is None or
        invalid_info.get('symbol') is None
    )
    assert is_invalid, "Invalid symbol should be detectable"
