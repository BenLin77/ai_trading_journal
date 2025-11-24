"""
資料庫操作測試

測試 database.py 的核心功能
"""

import pytest
import tempfile
import os
from database import TradingDatabase


@pytest.fixture
def temp_db():
    """建立臨時資料庫用於測試"""
    # 建立臨時檔案
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # 建立資料庫實例
    db = TradingDatabase(path)
    
    yield db
    
    # 清理
    try:
        os.unlink(path)
    except:
        pass


class TestTradingDatabase:
    """TradingDatabase 類別測試"""
    
    def test_database_initialization(self, temp_db):
        """測試資料庫初始化"""
        assert temp_db is not None
        # 驗證資料表已建立（透過查詢）
        trades = temp_db.get_trades()
        assert trades == []
    
    def test_add_trade(self, temp_db):
        """測試新增交易"""
        trade_data = {
            'datetime': '20251025',
            'symbol': 'AAPL',
            'action': 'BUY',
            'quantity': 100,
            'price': 150.50,
            'commission': 1.0,
            'realized_pnl': 0,
            'instrument_type': 'stock',
            'underlying': 'AAPL'
        }
        
        result = temp_db.add_trade(trade_data)
        assert result is True
        
        # 驗證已新增
        trades = temp_db.get_trades()
        assert len(trades) == 1
        assert trades[0]['symbol'] == 'AAPL'
    
    def test_add_duplicate_trade(self, temp_db):
        """測試重複新增交易（應被拒絕）"""
        trade_data = {
            'datetime': '20251025',
            'symbol': 'AAPL',
            'action': 'BUY',
            'quantity': 100,
            'price': 150.50,
            'commission': 1.0,
            'realized_pnl': 0,
            'instrument_type': 'stock',
            'underlying': 'AAPL'
        }
        
        # 第一次新增
        temp_db.add_trade(trade_data)
        
        # 第二次新增（重複）
        result = temp_db.add_trade(trade_data)
        assert result is False
        
        # 應該只有一筆
        trades = temp_db.get_trades()
        assert len(trades) == 1
    
    def test_get_trades_with_symbol_filter(self, temp_db):
        """測試按標的篩選交易"""
        # 新增多筆交易
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251026', 'symbol': 'TSLA', 'action': 'BUY',
            'quantity': 50, 'price': 250, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'TSLA'
        })
        
        # 查詢 AAPL
        aapl_trades = temp_db.get_trades(symbol='AAPL')
        assert len(aapl_trades) == 1
        assert aapl_trades[0]['symbol'] == 'AAPL'
    
    def test_get_trades_with_date_range(self, temp_db):
        """測試按日期範圍篩選（修復後的功能）"""
        # 新增不同日期的交易
        temp_db.add_trade({
            'datetime': '20251020', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'SELL',
            'quantity': 100, 'price': 155, 'commission': 1,
            'realized_pnl': 500, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251030', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 160, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        
        # 查詢 10/23 ~ 10/27（應該只包含 10/25 的交易）
        # 使用 YYYYMMDD 格式來測試修復後的功能
        trades = temp_db.get_trades(
            start_date='20251023',  # 直接使用資料庫格式
            end_date='20251027'
        )
        assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
        assert trades[0]['datetime'] == '20251025'
        
        # 測試 YYYY-MM-DD 格式也能正常工作（這是修復的部分）
        trades2 = temp_db.get_trades(
            start_date='2025-10-23',
            end_date='2025-10-27'
        )
        assert len(trades2) == 1, f"Expected 1 trade with dash format, got {len(trades2)}"
        assert trades2[0]['datetime'] == '20251025'
    
    def test_get_all_symbols(self, temp_db):
        """測試取得所有標的"""
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'TSLA', 'action': 'BUY',
            'quantity': 50, 'price': 250, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'TSLA'
        })
        
        symbols = temp_db.get_all_symbols()
        assert len(symbols) == 2
        assert 'AAPL' in symbols
        assert 'TSLA' in symbols
    
    def test_clear_database(self, temp_db):
        """測試清空資料庫"""
        # 新增交易
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 0, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        
        # 清空
        result = temp_db.clear_database()
        assert result is True
        
        # 驗證已清空
        trades = temp_db.get_trades()
        assert len(trades) == 0


class TestTradeStatistics:
    """測試統計功能"""
    
    def test_get_trade_statistics(self, temp_db):
        """測試交易統計"""
        # 新增測試數據
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 500, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251026', 'symbol': 'TSLA', 'action': 'SELL',
            'quantity': 50, 'price': 250, 'commission': 1,
            'realized_pnl': -200, 'instrument_type': 'stock', 'underlying': 'TSLA'
        })
        
        stats = temp_db.get_trade_statistics()
        
        assert stats['total_trades'] == 2
        assert stats['total_pnl'] == 300  # 500 - 200
        assert stats['wins'] == 1
        assert stats['losses'] == 1
    
    def test_get_pnl_by_symbol(self, temp_db):
        """測試按標的統計盈虧"""
        temp_db.add_trade({
            'datetime': '20251025', 'symbol': 'AAPL', 'action': 'BUY',
            'quantity': 100, 'price': 150, 'commission': 1,
            'realized_pnl': 500, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        temp_db.add_trade({
            'datetime': '20251026', 'symbol': 'AAPL', 'action': 'SELL',
            'quantity': 100, 'price': 155, 'commission': 1,
            'realized_pnl': 300, 'instrument_type': 'stock', 'underlying': 'AAPL'
        })
        
        pnl_by_symbol = temp_db.get_pnl_by_symbol()
        
        assert 'AAPL' in pnl_by_symbol
        assert pnl_by_symbol['AAPL'] == 800  # 500 + 300
