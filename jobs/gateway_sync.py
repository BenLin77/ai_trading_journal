"""
Gateway 數據定期同步任務

定期從 IB Gateway 獲取：
1. 即時持倉 -> 存入 open_positions 表
2. 當日成交 -> 存入 trades 表（避免重複）

使用方式：
- 在 APScheduler 中設定定期執行
- 建議每小時執行一次（交易時段）
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


async def sync_gateway_to_database(db) -> Dict[str, Any]:
    """
    從 IB Gateway 同步數據到資料庫
    
    使用同步方式獲取數據以避免事件循環衝突。
    
    Args:
        db: TradingDatabase 實例
        
    Returns:
        同步結果統計
    """
    result = {
        'success': False,
        'positions_synced': 0,
        'trades_synced': 0,
        'errors': []
    }
    
    try:
        from services.ib_service import get_ib_data_sync
        import os
        
        ib_host = os.getenv('IB_HOST', '127.0.0.1')
        ib_port = int(os.getenv('IB_PORT', '4001'))
        ib_client_id = int(os.getenv('IB_CLIENT_ID', '10'))
        
        logger.info(f"開始 Gateway 同步... (連接 {ib_host}:{ib_port})")
        
        # 使用同步函數獲取數據（避免事件循環衝突）
        ib_data = get_ib_data_sync(host=ib_host, port=ib_port, client_id=ib_client_id)
        
        if not ib_data['success']:
            raise ConnectionError(ib_data.get('error', '未知錯誤'))
        
        # 1. 同步持倉
        if ib_data['portfolio']:
            positions_data = []
            for p in ib_data['portfolio']:
                positions_data.append({
                    'symbol': p['symbol'],
                    'underlying': p['symbol'],
                    'position': p['position'],
                    'mark_price': p['market_price'],
                    'average_cost': p['avg_cost'],
                    'unrealized_pnl': p['unrealized_pnl'],
                    'realized_pnl': 0,
                    'asset_category': 'STK',
                    'strike': None,
                    'expiry': None,
                    'put_call': None,
                    'multiplier': 100,
                })
            
            count = db.upsert_open_positions(positions_data)
            result['positions_synced'] = count
            logger.info(f"同步 {count} 筆持倉到資料庫")
        
        # 2. 同步交易記錄
        trades_added = 0
        for t in ib_data['trades']:
            trade_data = {
                'datetime': t['time'],
                'symbol': t['symbol'],
                'action': 'BUY' if t['side'] == 'BOT' else 'SELL',
                'quantity': abs(t['quantity']),
                'price': t['price'],
                'commission': 0,
                'realized_pnl': 0,
                'instrument_type': 'stock',
                'underlying': t['symbol'],
            }
            
            if db.add_trade(trade_data):
                trades_added += 1
        
        result['trades_synced'] = trades_added
        if trades_added > 0:
            logger.info(f"同步 {trades_added} 筆新交易到資料庫")
        
        # 3. 同步帳戶損益統計
        if ib_data['pnl']:
            pnl = ib_data['pnl']
            net_liquidation = sum(p.get('market_price', 0) * p.get('position', 0) for p in ib_data['portfolio'])
            db.upsert_cash_snapshot(
                total_cash=net_liquidation,
                total_settled_cash=net_liquidation,
                currency='USD'
            )
            logger.info(f"同步帳戶淨值: ${net_liquidation:,.2f}")
        
        result['success'] = True
        logger.info("Gateway 同步完成")
        
    except ImportError:
        error_msg = "ib_insync 未安裝"
        result['errors'].append(error_msg)
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"Gateway 同步失敗: {str(e)}"
        result['errors'].append(error_msg)
        logger.error(error_msg)
    
    return result


async def run_gateway_sync_job(db) -> Dict[str, Any]:
    """
    排程任務入口點
    
    Args:
        db: TradingDatabase 實例
        
    Returns:
        執行結果
    """
    import os
    
    # 檢查是否使用 GATEWAY 模式
    data_source = os.getenv('DATA_SOURCE', 'QUERY').upper()
    
    if data_source != 'GATEWAY':
        logger.info(f"當前資料來源為 {data_source}，跳過 Gateway 同步")
        return {'success': True, 'skipped': True, 'reason': f'DATA_SOURCE={data_source}'}
    
    return await sync_gateway_to_database(db)


def check_market_hours() -> bool:
    """
    檢查是否在美股交易時段
    
    美股交易時段 (台灣時間):
    - 夏令時: 21:30 - 04:00
    - 冬令時: 22:30 - 05:00
    
    Returns:
        True 如果在交易時段
    """
    import pytz
    
    # 取得台灣時間
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    
    hour = now.hour
    
    # 簡化判斷：21:00 - 05:00 (涵蓋盤前盤後)
    if hour >= 21 or hour < 5:
        return True
    
    return False
