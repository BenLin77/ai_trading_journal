"""
IB Gateway/TWS 連線服務

使用 ib_insync 連接本地運行的 IB Gateway 或 TWS。
此版本使用子進程來完全隔離事件循環，避免與 FastAPI/APScheduler 衝突。
"""

import json
import logging
import subprocess
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PortfolioPosition:
    """持倉資料結構"""
    symbol: str
    underlying: str
    quantity: float
    avg_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    asset_category: str
    strike: Optional[float] = None
    expiry: Optional[str] = None
    put_call: Optional[str] = None
    multiplier: int = 100
    

@dataclass
class ExecutionRecord:
    """成交記錄資料結構"""
    symbol: str
    exec_id: str
    time: datetime
    side: str
    quantity: float
    price: float
    commission: float
    realized_pnl: float
    underlying: Optional[str] = None
    asset_category: str = 'STK'


@dataclass  
class PnLStatistics:
    """損益統計資料結構"""
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    net_liquidation: float


class IBService:
    """
    IB Gateway/TWS 連線服務
    
    使用子進程來完全隔離 IB 連線的事件循環。
    """
    
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 4001,
        client_id: int = 1,
        timeout: int = 30
    ):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self._data = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass  # 子進程已經斷開
        
    async def connect(self) -> bool:
        """使用子進程連線到 IB Gateway 並獲取數據"""
        self._data = get_ib_data_subprocess(
            host=self.host,
            port=self.port,
            client_id=self.client_id,
            timeout=self.timeout
        )
        
        if not self._data['success']:
            raise ConnectionError(self._data.get('error', '連線失敗'))
        
        logger.info(f"已從 IB Gateway 獲取數據 ({self.host}:{self.port})")
        return True
            
    async def disconnect(self):
        pass
            
    @property
    def is_connected(self) -> bool:
        return self._data is not None and self._data.get('success', False)
        
    async def get_portfolio_summary(self) -> List[PortfolioPosition]:
        """獲取當前持倉摘要"""
        if not self.is_connected:
            raise ConnectionError("尚未連接到 IB Gateway")
        
        positions = []
        for p in self._data.get('portfolio', []):
            position = PortfolioPosition(
                symbol=p['symbol'],
                underlying=p['symbol'],
                quantity=p['position'],
                avg_cost=p['avg_cost'],
                market_price=p['market_price'],
                market_value=p['market_value'],
                unrealized_pnl=p['unrealized_pnl'],
                realized_pnl=p['realized_pnl'],
                asset_category=p.get('asset_category', 'STK'),
                strike=p.get('strike'),
                expiry=p.get('expiry'),
                put_call=p.get('put_call'),
                multiplier=p.get('multiplier', 100)
            )
            positions.append(position)
            
        logger.info(f"獲取 {len(positions)} 筆持倉")
        return positions
        
    async def get_yesterday_trades(self) -> List[ExecutionRecord]:
        """獲取過去 24 小時的成交記錄"""
        if not self.is_connected:
            raise ConnectionError("尚未連接到 IB Gateway")
        
        trades = []
        for t in self._data.get('trades', []):
            record = ExecutionRecord(
                symbol=t['symbol'],
                exec_id=t.get('exec_id', ''),
                time=datetime.fromisoformat(t['time']) if isinstance(t['time'], str) else t['time'],
                side=t['side'],
                quantity=t['quantity'],
                price=t['price'],
                commission=t.get('commission', 0),
                realized_pnl=t.get('realized_pnl', 0),
                underlying=t.get('underlying', t['symbol']),
                asset_category=t.get('asset_category', 'STK')
            )
            trades.append(record)
            
        logger.info(f"獲取 {len(trades)} 筆昨日交易")
        return trades
        
    async def get_pnl_statistics(self) -> PnLStatistics:
        """獲取帳戶損益統計"""
        if not self.is_connected:
            raise ConnectionError("尚未連接到 IB Gateway")
        
        pnl = self._data.get('pnl', {})
        
        return PnLStatistics(
            unrealized_pnl=pnl.get('unrealized_pnl', 0),
            realized_pnl=pnl.get('realized_pnl', 0),
            total_pnl=pnl.get('total_pnl', 0),
            net_liquidation=pnl.get('net_liquidation', 0)
        )
        
    async def get_account_summary(self) -> Dict[str, Any]:
        """獲取帳戶摘要"""
        pnl = await self.get_pnl_statistics()
        return {
            'UnrealizedPnL': {'value': pnl.unrealized_pnl, 'currency': 'USD'},
            'RealizedPnL': {'value': pnl.realized_pnl, 'currency': 'USD'},
            'NetLiquidation': {'value': pnl.net_liquidation, 'currency': 'USD'},
        }


def create_ib_service_from_env() -> IBService:
    """從環境變數創建 IBService 實例"""
    import os
    
    host = os.getenv('IB_HOST', '127.0.0.1')
    port = int(os.getenv('IB_PORT', '4001'))
    client_id = int(os.getenv('IB_CLIENT_ID', '1'))
    
    return IBService(host=host, port=port, client_id=client_id)


def get_ib_data_subprocess(host: str = '127.0.0.1', port: int = 4001, 
                           client_id: int = 99, timeout: int = 30) -> Dict[str, Any]:
    """
    使用子進程獲取 IB 數據
    
    這樣可以完全隔離事件循環，避免與 FastAPI/APScheduler 衝突。
    """
    script = f'''
import json
import sys
from ib_insync import IB

result = {{
    'success': False,
    'portfolio': [],
    'trades': [],
    'pnl': {{}},
    'error': None
}}

ib = IB()

try:
    ib.connect('{host}', {port}, clientId={client_id}, timeout={timeout})
    
    if ib.isConnected():
        # 獲取持倉
        portfolio = ib.portfolio()
        result['portfolio'] = [
            {{
                'symbol': item.contract.localSymbol if item.contract.secType == 'OPT' else item.contract.symbol,
                'underlying': item.contract.symbol,
                'position': item.position,
                'avg_cost': item.averageCost,
                'market_price': item.marketPrice,
                'market_value': item.marketValue,
                'unrealized_pnl': item.unrealizedPNL,
                'realized_pnl': item.realizedPNL,
                'asset_category': item.contract.secType,
                'strike': item.contract.strike if item.contract.secType == 'OPT' else None,
                'expiry': item.contract.lastTradeDateOrContractMonth if item.contract.secType in ['OPT', 'FUT'] else None,
                'put_call': item.contract.right if item.contract.secType == 'OPT' else None,
                'multiplier': int(item.contract.multiplier) if item.contract.multiplier else 100,
            }}
            for item in portfolio
        ]
        
        # 獲取成交
        fills = ib.fills()
        result['trades'] = [
            {{
                'symbol': fill.contract.localSymbol if fill.contract.secType == 'OPT' else fill.contract.symbol,
                'underlying': fill.contract.symbol,
                'exec_id': fill.execution.execId,
                'time': str(fill.execution.time),
                'side': 'BUY' if fill.execution.side == 'BOT' else 'SELL',
                'quantity': fill.execution.shares,
                'price': fill.execution.price,
                'commission': fill.commissionReport.commission if fill.commissionReport else 0,
                'realized_pnl': fill.commissionReport.realizedPNL if fill.commissionReport else 0,
                'asset_category': fill.contract.secType,
            }}
            for fill in fills
        ]
        
        # 計算損益
        unrealized = sum(item.unrealizedPNL for item in portfolio)
        realized = sum(item.realizedPNL for item in portfolio)
        net_liquidation = sum(item.marketValue for item in portfolio)
        
        result['pnl'] = {{
            'unrealized_pnl': unrealized,
            'realized_pnl': realized,
            'total_pnl': unrealized + realized,
            'net_liquidation': net_liquidation,
        }}
        
        result['success'] = True
    else:
        result['error'] = '連線失敗'
        
except Exception as e:
    result['error'] = str(e)
finally:
    ib.disconnect()

print(json.dumps(result))
'''
    
    try:
        # 使用項目的 Python 環境
        python_path = sys.executable
        
        proc = subprocess.run(
            [python_path, '-c', script],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
            cwd='/root/ai_trading_journal'
        )
        
        if proc.returncode == 0 and proc.stdout.strip():
            result = json.loads(proc.stdout.strip())
            if result['success']:
                logger.info(f"子進程獲取 IB 數據成功: {len(result['portfolio'])} 持倉")
            return result
        else:
            error_msg = proc.stderr or "子進程執行失敗"
            logger.error(f"子進程錯誤: {error_msg}")
            return {'success': False, 'error': error_msg, 'portfolio': [], 'trades': [], 'pnl': {}}
            
    except subprocess.TimeoutExpired:
        logger.error("子進程超時")
        return {'success': False, 'error': '連線超時', 'portfolio': [], 'trades': [], 'pnl': {}}
    except json.JSONDecodeError as e:
        logger.error(f"解析子進程輸出失敗: {e}")
        return {'success': False, 'error': f'解析錯誤: {e}', 'portfolio': [], 'trades': [], 'pnl': {}}
    except Exception as e:
        logger.error(f"子進程獲取 IB 數據失敗: {e}")
        return {'success': False, 'error': str(e), 'portfolio': [], 'trades': [], 'pnl': {}}


# 為了向後兼容
def get_ib_data_sync(host: str = '127.0.0.1', port: int = 4001, client_id: int = 99) -> Dict[str, Any]:
    """同步方式獲取 IB 數據（使用子進程）"""
    return get_ib_data_subprocess(host, port, client_id)
