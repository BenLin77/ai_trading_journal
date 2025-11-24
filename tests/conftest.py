"""
Pytest 配置檔

提供全域 fixtures 和測試配置
"""

import pytest
import logging


# 全域配置
def pytest_configure(config):
    """Pytest 啟動時執行"""
    # 設定測試環境的 logging 等級
    logging.basicConfig(level=logging.WARNING)


# 全域 fixtures

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """建立測試數據目錄"""
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture
def sample_trade_data():
    """提供標準的交易數據範例"""
    return {
        'datetime': '20251025',
        'symbol': 'AAPL',
        'action': 'BUY',
        'quantity': 100,
        'price': 150.50,
        'commission': 1.0,
        'realized_pnl': 0,
        'instrument_type': 'stock',
        'underlying': 'AAPL',
        'strike': None,
        'expiry': None,
        'option_type': None,
        'multiplier': 1
    }


@pytest.fixture
def sample_option_trade_data():
    """提供選擇權交易數據範例"""
    return {
        'datetime': '20251025',
        'symbol': 'AAPL 20251220 C150',
        'action': 'BUY',
        'quantity': 10,
        'price': 5.50,
        'commission': 1.0,
        'realized_pnl': 0,
        'instrument_type': 'option',
        'underlying': 'AAPL',
        'strike': 150,
        'expiry': '20251220',
        'option_type': 'C',
        'multiplier': 100
    }


@pytest.fixture
def sample_trades_list():
    """提供多筆交易數據"""
    return [
        {
            'datetime': '20251020',
            'symbol': 'AAPL',
            'action': 'BUY',
            'quantity': 100,
            'price': 150.00,
            'commission': 1.0,
            'realized_pnl': 0,
            'instrument_type': 'stock',
            'underlying': 'AAPL'
        },
        {
            'datetime': '20251025',
            'symbol': 'AAPL',
            'action': 'SELL',
            'quantity': 100,
            'price': 155.00,
            'commission': 1.0,
            'realized_pnl': 500,
            'instrument_type': 'stock',
            'underlying': 'AAPL'
        },
        {
            'datetime': '20251026',
            'symbol': 'TSLA',
            'action': 'BUY',
            'quantity': 50,
            'price': 250.00,
            'commission': 1.0,
            'realized_pnl': 0,
            'instrument_type': 'stock',
            'underlying': 'TSLA'
        }
    ]
