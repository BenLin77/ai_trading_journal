"""
IB Gateway/TWS 連線服務

使用 ib_insync 連接本地運行的 IB Gateway 或 TWS，
提供即時持倉、交易記錄、損益統計等功能。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

# 在模組載入時應用 nest_asyncio（必須在任何 event loop 操作之前）
try:
    import nest_asyncio
    nest_asyncio.apply()
    logger.debug("nest_asyncio applied successfully")
except ImportError:
    logger.warning("nest_asyncio not installed, IB Gateway connection may fail in async context")


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
    asset_category: str  # 'STK', 'OPT', 'FUT'
    # 選擇權特有欄位
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
    side: str  # 'BUY' or 'SELL'
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
    
    使用 ib_insync 異步連接 IB，提供數據抓取功能。
    支援 async context manager 模式自動管理連線。
    
    Usage:
        async with IBService(host='127.0.0.1', port=4001) as ib:
            positions = await ib.get_portfolio_summary()
            trades = await ib.get_yesterday_trades()
            pnl = await ib.get_pnl_statistics()
    """
    
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 4001,
        client_id: int = 1,
        timeout: int = 30
    ):
        """
        初始化 IB 連線服務
        
        Args:
            host: IB Gateway 主機地址
            port: IB Gateway 端口 (TWS: 7497/7496, Gateway: 4001/4002)
            client_id: 客戶端 ID (每個連線需唯一)
            timeout: 連線超時時間 (秒)
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.timeout = timeout
        self._ib = None
        self._connected = False
        
    async def __aenter__(self):
        """異步上下文管理器入口"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        await self.disconnect()
        
    async def connect(self) -> bool:
        """
        建立連線到 IB Gateway/TWS
        
        Returns:
            bool: 連線成功返回 True
            
        Raises:
            ConnectionError: 連線失敗時拋出
        """
        try:
            from ib_insync import IB
            
            self._ib = IB()
            
            # 在單獨的線程中執行同步連線以避免 event loop 衝突
            def _sync_connect():
                """在獨立線程中執行連線"""
                try:
                    self._ib.connect(
                        self.host,
                        self.port,
                        clientId=self.client_id,
                        timeout=self.timeout
                    )
                    return self._ib.isConnected()
                except Exception as e:
                    logger.error(f"線程內連線失敗: {e}")
                    return False
            
            # 使用線程執行器
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                connected = await loop.run_in_executor(executor, _sync_connect)
            
            if connected:
                self._connected = True
                logger.info(f"已連接到 IB Gateway ({self.host}:{self.port})")
                return True
            else:
                raise ConnectionError("連線建立失敗")
                
        except asyncio.TimeoutError:
            raise ConnectionError(f"連線超時 ({self.timeout}秒)")
        except ImportError:
            raise ImportError("ib_insync 未安裝，請執行: pip install ib_insync")
        except Exception as e:
            logger.error(f"IB 連線失敗: {e}")
            raise ConnectionError(f"無法連接 IB Gateway: {str(e)}")
            
    async def disconnect(self):
        """斷開連線"""
        if self._ib and self._connected:
            self._ib.disconnect()
            self._connected = False
            logger.info("IB 連線已斷開")
            
    @property
    def is_connected(self) -> bool:
        """檢查是否已連線"""
        return self._connected and self._ib and self._ib.isConnected()
        
    def _ensure_connected(self):
        """確保已連線"""
        if not self.is_connected:
            raise ConnectionError("尚未連接到 IB Gateway")
            
    async def get_portfolio_summary(self) -> List[PortfolioPosition]:
        """
        獲取當前持倉摘要
        
        Returns:
            List[PortfolioPosition]: 持倉列表
        """
        self._ensure_connected()
        
        positions = []
        
        # 獲取投資組合項目
        portfolio = self._ib.portfolio()
        
        for item in portfolio:
            contract = item.contract
            
            # 判斷資產類型
            asset_category = 'STK'
            if contract.secType == 'OPT':
                asset_category = 'OPT'
            elif contract.secType == 'FUT':
                asset_category = 'FUT'
                
            position = PortfolioPosition(
                symbol=contract.symbol if asset_category == 'STK' else contract.localSymbol,
                underlying=contract.symbol,
                quantity=item.position,
                avg_cost=item.averageCost,
                market_price=item.marketPrice,
                market_value=item.marketValue,
                unrealized_pnl=item.unrealizedPNL,
                realized_pnl=item.realizedPNL,
                asset_category=asset_category,
                strike=contract.strike if asset_category == 'OPT' else None,
                expiry=contract.lastTradeDateOrContractMonth if asset_category in ['OPT', 'FUT'] else None,
                put_call=contract.right if asset_category == 'OPT' else None,
                multiplier=int(contract.multiplier) if contract.multiplier else 100
            )
            positions.append(position)
            
        logger.info(f"獲取 {len(positions)} 筆持倉")
        return positions
        
    async def get_yesterday_trades(self) -> List[ExecutionRecord]:
        """
        獲取過去 24 小時的成交記錄
        
        Returns:
            List[ExecutionRecord]: 成交記錄列表
        """
        self._ensure_connected()
        
        trades = []
        
        # 獲取成交記錄
        executions = self._ib.executions()
        
        # 計算 24 小時前的時間點
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for fill in self._ib.fills():
            exec_info = fill.execution
            contract = fill.contract
            
            # 過濾 24 小時內的交易
            exec_time = exec_info.time
            if isinstance(exec_time, str):
                exec_time = datetime.fromisoformat(exec_time.replace('Z', '+00:00'))
            
            if exec_time < cutoff_time:
                continue
                
            # 判斷資產類型
            asset_category = 'STK'
            if contract.secType == 'OPT':
                asset_category = 'OPT'
            elif contract.secType == 'FUT':
                asset_category = 'FUT'
                
            record = ExecutionRecord(
                symbol=contract.localSymbol if asset_category != 'STK' else contract.symbol,
                exec_id=exec_info.execId,
                time=exec_time,
                side='BUY' if exec_info.side == 'BOT' else 'SELL',
                quantity=exec_info.shares,
                price=exec_info.price,
                commission=fill.commissionReport.commission if fill.commissionReport else 0,
                realized_pnl=fill.commissionReport.realizedPNL if fill.commissionReport else 0,
                underlying=contract.symbol,
                asset_category=asset_category
            )
            trades.append(record)
            
        logger.info(f"獲取 {len(trades)} 筆昨日交易")
        return trades
        
    async def get_pnl_statistics(self) -> PnLStatistics:
        """
        獲取帳戶損益統計
        
        Returns:
            PnLStatistics: 損益統計
        """
        self._ensure_connected()
        
        # 獲取帳戶摘要
        account_values = self._ib.accountSummary()
        
        unrealized_pnl = 0.0
        realized_pnl = 0.0
        net_liquidation = 0.0
        
        for av in account_values:
            if av.tag == 'UnrealizedPnL':
                unrealized_pnl = float(av.value)
            elif av.tag == 'RealizedPnL':
                realized_pnl = float(av.value)
            elif av.tag == 'NetLiquidation':
                net_liquidation = float(av.value)
                
        total_pnl = unrealized_pnl + realized_pnl
        
        logger.info(f"損益統計: 未實現={unrealized_pnl}, 已實現={realized_pnl}")
        
        return PnLStatistics(
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            total_pnl=total_pnl,
            net_liquidation=net_liquidation
        )
        
    async def get_account_summary(self) -> Dict[str, Any]:
        """
        獲取帳戶摘要（含更多細節）
        
        Returns:
            Dict: 帳戶摘要資訊
        """
        self._ensure_connected()
        
        account_values = self._ib.accountSummary()
        
        summary = {}
        for av in account_values:
            summary[av.tag] = {
                'value': av.value,
                'currency': av.currency,
                'account': av.account
            }
            
        return summary


# 工廠函數：便於從環境變數創建實例
def create_ib_service_from_env() -> IBService:
    """
    從環境變數創建 IBService 實例
    
    環境變數:
        - IB_HOST: IB Gateway 主機 (預設: 127.0.0.1)
        - IB_PORT: IB Gateway 端口 (預設: 4001)
        - IB_CLIENT_ID: 客戶端 ID (預設: 1)
    """
    import os
    
    host = os.getenv('IB_HOST', '127.0.0.1')
    port = int(os.getenv('IB_PORT', '4001'))
    client_id = int(os.getenv('IB_CLIENT_ID', '1'))
    
    return IBService(host=host, port=port, client_id=client_id)
