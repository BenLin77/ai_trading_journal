"""
PnL Calculator Module

負責根據交易歷史計算已實現盈虧 (Realized PnL)。
採用 FIFO (First-In-First-Out) 邏輯。
"""

import pandas as pd
from typing import List

from utils.derivatives_support import InstrumentParser

class PnLCalculator:
    def __init__(self, db):
        self.db = db

    def fix_missing_multipliers(self):
        """檢查並修復資料庫中遺漏的 Multiplier"""
        trades = self.db.get_trades()
        if not trades:
            return

        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        
        for trade in trades:
            # 如果 multiplier 為 1 或 None，嘗試重新解析
            current_multiplier = trade['multiplier']
            if not current_multiplier or current_multiplier == 1:
                parsed = InstrumentParser.parse_symbol(trade['symbol'])
                
                # 如果解析出是 Option 且 multiplier 為 100，則更新
                if parsed['instrument_type'] == 'option' and parsed['multiplier'] == 100:
                    cursor.execute("""
                        UPDATE trades 
                        SET multiplier = ?, instrument_type = ?, strike = ?, expiry = ?, option_type = ?, underlying = ?
                        WHERE trade_id = ?
                    """, (
                        parsed['multiplier'],
                        parsed['instrument_type'],
                        parsed['strike'],
                        parsed['expiry'],
                        parsed['option_type'],
                        parsed['underlying'],
                        trade['trade_id']
                    ))
                    updated_count += 1
        
        if updated_count > 0:
            conn.commit()
            print(f"Fixed multipliers for {updated_count} trades.")
            
        conn.close()

    def recalculate_all(self):
        """重新計算資料庫中所有交易的盈虧"""
        # 0. 先修復資料
        self.fix_missing_multipliers()
        
        # 1. 取得所有交易
        trades = self.db.get_trades()
        if not trades:
            return

        # 轉為 DataFrame 方便處理
        df = pd.DataFrame(trades)
        
        # 確保時間排序
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')

        # 2. 按標的的分組計算
        symbols = df['symbol'].unique()
        
        updates = []

        for symbol in symbols:
            symbol_trades = df[df['symbol'] == symbol].copy()
            updates.extend(self._calculate_symbol_pnl(symbol_trades))

        # 3. 批量更新資料庫（效能優化）
        if updates:
            import logging
            logging.info(f"Batch updating PnL for {len(updates)} trades...")

            conn = self.db._get_connection()
            cursor = conn.cursor()

            try:
                # 批量更新：executemany 一次性執行多筆 SQL
                cursor.executemany(
                    "UPDATE trades SET realized_pnl = ? WHERE trade_id = ?",
                    [(pnl, trade_id) for trade_id, pnl in updates]
                )
                conn.commit()
                logging.info(f"Successfully updated {len(updates)} trades")
            except Exception as e:
                conn.rollback()
                logging.error(f"Batch update failed: {str(e)}")
                raise
            finally:
                conn.close()

    def _calculate_symbol_pnl(self, df: pd.DataFrame) -> List[tuple]:
        """
        計算單一標的的盈虧（FIFO）

        Args:
            df: 單一標的的所有交易記錄

        Returns:
            (trade_id, realized_pnl) 的列表
        """
        open_positions = []  # 持倉佇列: [{'price': float, 'qty': signed_qty, 'multiplier': float}]
        updates = []

        for _, row in df.iterrows():
            trade_id = row['trade_id']
            action = row['action'].upper()
            price = float(row['price'])
            qty = abs(float(row['quantity']))
            multiplier = float(row['multiplier']) if pd.notna(row['multiplier']) and row['multiplier'] else 1.0

            # 確保 multiplier 正確設置（選擇權應為 100）
            if multiplier == 1.0 and 'option' in str(row.get('instrument_type', '')).lower():
                multiplier = 100.0

            # 標準化動作名稱
            if action in ['BOT', 'BUY']:
                signed_qty = qty  # 買入為正
            elif action in ['SLD', 'SELL']:
                signed_qty = -qty  # 賣出為負
            else:
                signed_qty = qty if action == 'BUY' else -qty

            current_trade_pnl = 0.0
            remaining_qty = signed_qty

            # FIFO 配對邏輯
            while remaining_qty != 0:
                if not open_positions:
                    # 無持倉，建立新部位（開倉）
                    open_positions.append({
                        'price': price,
                        'qty': remaining_qty,
                        'multiplier': multiplier
                    })
                    remaining_qty = 0
                else:
                    head = open_positions[0]
                    head_qty = head['qty']
                    head_multiplier = head.get('multiplier', 1.0)

                    # 同向 -> 加倉
                    if (remaining_qty > 0 and head_qty > 0) or (remaining_qty < 0 and head_qty < 0):
                        open_positions.append({
                            'price': price,
                            'qty': remaining_qty,
                            'multiplier': multiplier
                        })
                        remaining_qty = 0
                    else:
                        # 反向 -> 平倉
                        if abs(remaining_qty) >= abs(head_qty):
                            # 完全平倉頭部
                            open_positions.pop(0)

                            if head_qty > 0:  # 平多倉
                                pnl_chunk = (price - head['price']) * abs(head_qty) * head_multiplier
                            else:  # 平空倉
                                pnl_chunk = (head['price'] - price) * abs(head_qty) * head_multiplier

                            current_trade_pnl += pnl_chunk
                            remaining_qty += head_qty

                        else:
                            # 部分平倉
                            if head_qty > 0:  # 平多倉
                                pnl_chunk = (price - head['price']) * abs(remaining_qty) * head_multiplier
                            else:  # 平空倉
                                pnl_chunk = (head['price'] - price) * abs(remaining_qty) * head_multiplier

                            current_trade_pnl += pnl_chunk
                            head['qty'] += remaining_qty
                            remaining_qty = 0

            # 四捨五入到小數點 2 位
            updates.append((trade_id, round(current_trade_pnl, 2)))

        return updates
