"""
統一的資料載入模組

此模組負責：
1. 管理資料庫單例
2. 提供快取的資料載入函式
3. 統一錯誤處理
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from database import TradingDatabase
from utils.error_handler import handle_errors
from utils.logging_config import get_logger

logger = get_logger(__name__)


@st.cache_resource
def get_database() -> TradingDatabase:
    """
    取得資料庫單例
    
    使用 Streamlit cache_resource 確保整個應用只有一個資料庫實例
    
    Returns:
        TradingDatabase 實例
    """
    logger.info("Initializing database connection")
    return TradingDatabase()


@st.cache_data(ttl=300)
@handle_errors("無法載入交易數據", default_return=[])
def load_all_trades() -> List[Dict[str, Any]]:
    """
    載入所有交易（快取 5 分鐘）
    
    Returns:
        交易列表
    """
    db = get_database()
    trades = db.get_trades()
    logger.info(f"Loaded {len(trades)} trades")
    return trades


@st.cache_data(ttl=300)
@handle_errors("無法載入指定標的的交易數據", default_return=[])
def load_trades_by_symbol(symbol: str) -> List[Dict[str, Any]]:
    """
    按標的載入交易（快取）
    
    Args:
        symbol: 標的代號
        
    Returns:
        交易列表
    """
    db = get_database()
    trades = db.get_trades(symbol=symbol)
    logger.info(f"Loaded {len(trades)} trades for {symbol}")
    return trades


@st.cache_data(ttl=300)
@handle_errors("無法載入日期範圍內的交易數據", default_return=[])
def load_trades_by_date_range(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    按日期範圍載入交易（快取）
    
    Args:
        symbol: 標的代號（可選）
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        交易列表
    """
    db = get_database()
    trades = db.get_trades(symbol=symbol, start_date=start_date, end_date=end_date)
    logger.info(f"Loaded {len(trades)} trades (symbol={symbol}, dates={start_date}~{end_date})")
    return trades


@st.cache_data(ttl=300)
@handle_errors("無法載入交易統計", default_return={})
def load_trade_statistics() -> Dict[str, Any]:
    """
    載入交易統計（快取）
    
    Returns:
        統計資料字典
    """
    db = get_database()
    stats = db.get_trade_statistics()
    logger.info(f"Loaded statistics: {stats.get('total_trades', 0)} trades, ${stats.get('total_pnl', 0):.2f} PnL")
    return stats


@st.cache_data(ttl=300)
@handle_errors("無法載入標的列表", default_return=[])
def load_all_symbols() -> List[str]:
    """
    載入所有標的代號（快取）
    
    Returns:
        標的代號列表
    """
    db = get_database()
    symbols = db.get_all_symbols()
    logger.info(f"Loaded {len(symbols)} symbols")
    return symbols


@st.cache_data(ttl=300)
@handle_errors("無法載入按標的分組的盈虧", default_return={})
def load_pnl_by_symbol() -> Dict[str, float]:
    """
    載入按標的分組的盈虧（快取）
    
    Returns:
        標的代號 -> 總盈虧的字典
    """
    db = get_database()
    pnl_data = db.get_pnl_by_symbol()
    logger.info(f"Loaded PnL data for {len(pnl_data)} symbols")
    return pnl_data


@handle_errors("無法轉換為 DataFrame", default_return=pd.DataFrame())
def trades_to_dataframe(trades: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    將交易列表轉為 DataFrame 並處理日期
    
    Args:
        trades: 交易列表
        
    Returns:
        處理後的 DataFrame
    """
    if not trades:
        return pd.DataFrame()
    
    df = pd.DataFrame(trades)
    
    # 統一處理日期轉換
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    logger.debug(f"Converted {len(df)} trades to DataFrame")
    return df


def clear_cache():
    """清除所有快取"""
    st.cache_data.clear()
    logger.info("All data cache cleared")


def refresh_trades():
    """
    強制重新載入交易數據
    
    清除快取並重新載入
    """
    clear_cache()
    logger.info("Refreshing trade data")
    return load_all_trades()
