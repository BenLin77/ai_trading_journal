"""
報告數據服務模組

根據 DATA_SOURCE 環境變數決定資料來源：
- QUERY: 從 IBKR Flex Query (CSV/XML) 讀取
- GATEWAY: 從 IB Gateway/TWS 即時連線讀取
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ReportContext:
    """報告上下文數據結構"""
    report_date: str
    portfolio_summary: List[Dict[str, Any]]
    yesterday_trades: List[Dict[str, Any]]
    pnl_statistics: Dict[str, Any]
    cash_balance: Optional[Dict[str, Any]] = None
    data_source: str = 'QUERY'
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReportDataService:
    """
    報告數據服務
    
    根據環境變數 DATA_SOURCE 決定使用哪種方式取得資料：
    - QUERY: 使用 IBKR Flex Query API (預設)
    - GATEWAY: 使用 IB Gateway 即時連線
    """
    
    def __init__(self, db=None):
        """
        初始化報告數據服務
        
        Args:
            db: TradingDatabase 實例 (用於 QUERY 模式)
        """
        self.db = db
        self._data_source = os.getenv('DATA_SOURCE', 'QUERY').upper()
        
        # IB Gateway 設定 (用於 GATEWAY 模式)
        self._ib_host = os.getenv('IB_HOST', '127.0.0.1')
        self._ib_port = int(os.getenv('IB_PORT', '4001'))
        self._ib_client_id = int(os.getenv('IB_CLIENT_ID', '1'))
        
    @property
    def data_source(self) -> str:
        """取得當前資料來源設定"""
        return self._data_source
        
    async def generate_daily_report_context(self) -> ReportContext:
        """
        生成每日報告所需的上下文數據
        
        根據 DATA_SOURCE 設定自動選擇資料來源。
        
        Returns:
            ReportContext: 報告上下文數據
        """
        if self._data_source == 'GATEWAY':
            return await self._fetch_from_gateway()
        else:
            return await self._fetch_from_query()
            
    async def _fetch_from_gateway(self) -> ReportContext:
        """
        從 IB Gateway 獲取即時數據
        """
        from services.ib_service import IBService
        
        logger.info("正在從 IB Gateway 獲取數據...")
        
        try:
            async with IBService(
                host=self._ib_host,
                port=self._ib_port,
                client_id=self._ib_client_id
            ) as ib:
                # 1. 獲取持倉
                positions = await ib.get_portfolio_summary()
                portfolio_summary = [
                    {
                        'symbol': p.symbol,
                        'underlying': p.underlying,
                        'quantity': p.quantity,
                        'avg_cost': p.avg_cost,
                        'market_price': p.market_price,
                        'market_value': p.market_value,
                        'unrealized_pnl': p.unrealized_pnl,
                        'realized_pnl': p.realized_pnl,
                        'asset_category': p.asset_category,
                        'strike': p.strike,
                        'expiry': p.expiry,
                        'put_call': p.put_call,
                        'multiplier': p.multiplier
                    }
                    for p in positions
                ]
                
                # 2. 獲取昨日交易
                trades = await ib.get_yesterday_trades()
                yesterday_trades = [
                    {
                        'symbol': t.symbol,
                        'exec_id': t.exec_id,
                        'time': t.time.isoformat() if isinstance(t.time, datetime) else str(t.time),
                        'side': t.side,
                        'quantity': t.quantity,
                        'price': t.price,
                        'commission': t.commission,
                        'realized_pnl': t.realized_pnl,
                        'underlying': t.underlying,
                        'asset_category': t.asset_category
                    }
                    for t in trades
                ]
                
                # 3. 獲取損益統計
                pnl = await ib.get_pnl_statistics()
                pnl_statistics = {
                    'unrealizedPnL': pnl.unrealized_pnl,
                    'realizedPnL': pnl.realized_pnl,
                    'totalPnL': pnl.total_pnl,
                    'netLiquidation': pnl.net_liquidation
                }
                
            logger.info(f"IB Gateway 數據獲取完成: {len(portfolio_summary)} 持倉, {len(yesterday_trades)} 交易")
            
            return ReportContext(
                report_date=datetime.now().strftime('%Y-%m-%d'),
                portfolio_summary=portfolio_summary,
                yesterday_trades=yesterday_trades,
                pnl_statistics=pnl_statistics,
                data_source='GATEWAY'
            )
            
        except Exception as e:
            logger.error(f"IB Gateway 連線失敗: {e}")
            raise ConnectionError(f"無法連接 IB Gateway: {str(e)}")
            
    async def _fetch_from_query(self) -> ReportContext:
        """
        從 IBKR Flex Query / 資料庫獲取數據
        """
        logger.info("正在從資料庫/Flex Query 獲取數據...")
        
        if not self.db:
            raise ValueError("QUERY 模式需要提供 db 實例")
            
        # 1. 獲取持倉
        positions = self.db.get_latest_positions()
        portfolio_summary = []
        
        for p in positions:
            portfolio_summary.append({
                'symbol': p.get('symbol', ''),
                'underlying': p.get('underlying', p.get('symbol', '')),
                'quantity': p.get('position', p.get('quantity', 0)),
                'avg_cost': p.get('average_cost', p.get('avg_cost', 0)),
                'market_price': p.get('mark_price', p.get('market_price', 0)),
                'market_value': p.get('market_value', 0),
                'unrealized_pnl': p.get('unrealized_pnl', 0),
                'realized_pnl': p.get('realized_pnl', 0),
                'asset_category': p.get('asset_category', 'STK'),
                'strike': p.get('strike'),
                'expiry': p.get('expiry'),
                'put_call': p.get('put_call'),
                'multiplier': p.get('multiplier', 100)
            })
            
        # 2. 獲取昨日交易 (過去 24 小時)
        all_trades = self.db.get_trades()
        yesterday = datetime.now() - timedelta(hours=24)
        
        yesterday_trades = []
        for t in all_trades:
            try:
                trade_time_str = t.get('datetime', '')
                if len(trade_time_str) == 8:  # YYYYMMDD format
                    trade_time = datetime.strptime(trade_time_str, '%Y%m%d')
                else:
                    trade_time = datetime.fromisoformat(trade_time_str.replace('Z', '+00:00'))
                    
                if trade_time >= yesterday:
                    yesterday_trades.append({
                        'symbol': t.get('symbol', ''),
                        'time': trade_time.isoformat(),
                        'side': t.get('action', '').upper(),
                        'quantity': t.get('quantity', 0),
                        'price': t.get('price', 0),
                        'commission': t.get('commission', 0),
                        'realized_pnl': t.get('realized_pnl', 0)
                    })
            except Exception:
                continue
                
        # 3. 計算損益統計
        total_unrealized = sum(p.get('unrealized_pnl', 0) for p in portfolio_summary)
        total_realized = sum(t.get('realized_pnl', 0) for t in yesterday_trades)
        
        pnl_statistics = {
            'unrealizedPnL': total_unrealized,
            'realizedPnL': total_realized,
            'totalPnL': total_unrealized + total_realized,
            'netLiquidation': sum(p.get('market_value', 0) for p in portfolio_summary)
        }
        
        # 4. 獲取現金餘額
        cash_balance = None
        try:
            cash = self.db.get_latest_cash_snapshot()
            if cash:
                cash_balance = {
                    'total_cash': cash.get('total_cash', 0),
                    'ending_cash': cash.get('ending_cash', 0),
                    'ending_settled_cash': cash.get('ending_settled_cash', 0),
                    'currency': cash.get('currency', 'USD')
                }
        except Exception:
            pass
            
        logger.info(f"資料庫數據獲取完成: {len(portfolio_summary)} 持倉, {len(yesterday_trades)} 交易")
        
        return ReportContext(
            report_date=datetime.now().strftime('%Y-%m-%d'),
            portfolio_summary=portfolio_summary,
            yesterday_trades=yesterday_trades,
            pnl_statistics=pnl_statistics,
            cash_balance=cash_balance,
            data_source='QUERY'
        )


# 便捷函數
async def generate_daily_report_context(db=None) -> ReportContext:
    """
    便捷函數：生成每日報告上下文
    
    Args:
        db: TradingDatabase 實例 (QUERY 模式必須)
        
    Returns:
        ReportContext: 報告上下文數據
    """
    service = ReportDataService(db=db)
    return await service.generate_daily_report_context()
