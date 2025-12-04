"""
選擇權策略自動識別模組

自動識別常見的選擇權組合策略
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd


class OptionStrategyDetector:
    """選擇權策略識別器"""

    # 策略定義
    STRATEGIES = {
        # 價差策略 (Spreads)
        'bull_call_spread': {
            'name': 'Bull Call Spread（牛市看漲價差）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'C', 'strike': 'lower'},
                {'action': 'SELL', 'option_type': 'C', 'strike': 'higher'}
            ],
            'description': '買低履約價 Call + 賣高履約價 Call，看漲但限制獲利'
        },
        'bear_call_spread': {
            'name': 'Bear Call Spread（熊市看跌價差）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'strike': 'lower'},
                {'action': 'BUY', 'option_type': 'C', 'strike': 'higher'}
            ],
            'description': '賣低履約價 Call + 買高履約價 Call，看跌並收取權利金'
        },
        'bull_put_spread': {
            'name': 'Bull Put Spread（牛市看漲賣權價差）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'P', 'strike': 'higher'},
                {'action': 'BUY', 'option_type': 'P', 'strike': 'lower'}
            ],
            'description': '賣高履約價 Put + 買低履約價 Put，看漲並收取權利金'
        },
        'bear_put_spread': {
            'name': 'Bear Put Spread（熊市看跌價差）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'P', 'strike': 'higher'},
                {'action': 'SELL', 'option_type': 'P', 'strike': 'lower'}
            ],
            'description': '買高履約價 Put + 賣低履約價 Put，看跌但限制成本'
        },

        # 跨式策略 (Straddles & Strangles)
        'long_straddle': {
            'name': 'Long Straddle（買入跨式）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'C', 'strike': 'same'},
                {'action': 'BUY', 'option_type': 'P', 'strike': 'same'}
            ],
            'description': '同履約價買 Call + Put，預期大幅波動'
        },
        'short_straddle': {
            'name': 'Short Straddle（賣出跨式）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'strike': 'same'},
                {'action': 'SELL', 'option_type': 'P', 'strike': 'same'}
            ],
            'description': '同履約價賣 Call + Put，預期盤整不動'
        },
        'long_strangle': {
            'name': 'Long Strangle（買入勒式）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'C', 'strike': 'higher'},
                {'action': 'BUY', 'option_type': 'P', 'strike': 'lower'}
            ],
            'description': '不同履約價買 Call + Put，預期大幅波動但成本較低'
        },
        'short_strangle': {
            'name': 'Short Strangle（賣出勒式）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'strike': 'higher'},
                {'action': 'SELL', 'option_type': 'P', 'strike': 'lower'}
            ],
            'description': '不同履約價賣 Call + Put，預期盤整並收取權利金'
        },

        # 蝶式與鐵鷹策略
        'iron_condor': {
            'name': 'Iron Condor（鐵鷹式）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'P', 'strike': 'lower_mid'},
                {'action': 'BUY', 'option_type': 'P', 'strike': 'lowest'},
                {'action': 'SELL', 'option_type': 'C', 'strike': 'higher_mid'},
                {'action': 'BUY', 'option_type': 'C', 'strike': 'highest'}
            ],
            'description': '同時建立 Bull Put Spread + Bear Call Spread，預期價格在區間內'
        },

        # 保護性策略
        'protective_put': {
            'name': 'Protective Put（保護性賣權）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'P', 'has_stock': True}
            ],
            'description': '持有股票並買入 Put 避險'
        },
        'covered_call': {
            'name': 'Covered Call（備兌看漲）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'has_stock': True}
            ],
            'description': '持有股票並賣出 Call 收取權利金'
        },
        'collar': {
            'name': 'Collar（領口策略）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'has_stock': True},
                {'action': 'BUY', 'option_type': 'P', 'has_stock': True}
            ],
            'description': '持有股票 + 賣出 Call + 買入 Put，鎖定獲利區間並保護下檔風險'
        },
        'synthetic_long': {
            'name': 'Synthetic Long（合成多頭）',
            'pattern': [
                {'action': 'BUY', 'option_type': 'C', 'strike': 'same'},
                {'action': 'SELL', 'option_type': 'P', 'strike': 'same'}
            ],
            'description': '同履約價買 Call + 賣 Put，模擬持有正股'
        },
        'synthetic_short': {
            'name': 'Synthetic Short（合成空頭）',
            'pattern': [
                {'action': 'SELL', 'option_type': 'C', 'strike': 'same'},
                {'action': 'BUY', 'option_type': 'P', 'strike': 'same'}
            ],
            'description': '同履約價賣 Call + 買 Put，模擬放空正股'
        }
    }

    @staticmethod
    def detect_strategies(trades: List[Dict], time_window_minutes: int = 5) -> List[Dict]:
        """
        從交易列表中識別選擇權策略組合

        Args:
            trades: 交易記錄列表
            time_window_minutes: 判斷為同一策略的時間窗口（分鐘）

        Returns:
            識別出的策略列表
        """
        if not trades:
            return []

        # 轉換為 DataFrame 方便處理
        df = pd.DataFrame(trades)

        # 只處理選擇權交易
        option_trades = df[df['instrument_type'] == 'option'].copy()

        if len(option_trades) == 0:
            return []

        # 確保 datetime 是 datetime 類型
        option_trades['datetime'] = pd.to_datetime(option_trades['datetime'])

        # 按標的和時間分組
        strategies = []

        for underlying in option_trades['underlying'].unique():
            underlying_trades = option_trades[option_trades['underlying'] == underlying].copy()
            underlying_trades = underlying_trades.sort_values('datetime')

            # 時間窗口分組
            groups = []
            current_group = []
            last_time = None

            for _, trade in underlying_trades.iterrows():
                current_time = trade['datetime']

                if last_time is None or (current_time - last_time).total_seconds() <= time_window_minutes * 60:
                    current_group.append(trade)
                else:
                    if len(current_group) > 1:
                        groups.append(current_group)
                    current_group = [trade]

                last_time = current_time

            # 最後一組
            if len(current_group) > 1:
                groups.append(current_group)

            # 識別每組的策略
            for group in groups:
                detected = OptionStrategyDetector._identify_strategy(group)
                if detected:
                    strategies.append(detected)

        return strategies

    @staticmethod
    def _identify_strategy(trades: List) -> Optional[Dict]:
        """識別一組交易的策略類型"""

        if len(trades) < 2:
            return None

        # 提取關鍵資訊
        legs = []
        for trade in trades:
            legs.append({
                'action': trade['action'],
                'option_type': trade['option_type'],
                'strike': float(trade['strike']) if trade['strike'] else 0,
                'quantity': trade['quantity'],
                'price': trade['price'],
                'expiry': trade['expiry'],
                'datetime': trade['datetime'],
                'symbol': trade['symbol']
            })

        # 按履約價排序
        legs_sorted = sorted(legs, key=lambda x: x['strike'])

        # 檢查各種策略模式
        for strategy_key, strategy_def in OptionStrategyDetector.STRATEGIES.items():
            if OptionStrategyDetector._match_pattern(legs_sorted, strategy_def['pattern']):
                return {
                    'strategy_type': strategy_key,
                    'strategy_name': strategy_def['name'],
                    'description': strategy_def['description'],
                    'underlying': trades[0]['underlying'],
                    'legs': legs,
                    'datetime': trades[0]['datetime'],
                    'expiry': trades[0]['expiry'],
                    'total_cost': sum(
                        leg['price'] * leg['quantity'] * (1 if leg['action'] == 'BUY' else -1)
                        for leg in legs
                    )
                }

        # 無法識別的策略
        return {
            'strategy_type': 'custom',
            'strategy_name': 'Custom Strategy（自訂策略）',
            'description': f'包含 {len(legs)} 個選擇權部位',
            'underlying': trades[0]['underlying'],
            'legs': legs,
            'datetime': trades[0]['datetime'],
            'expiry': trades[0]['expiry'],
            'total_cost': sum(
                leg['price'] * leg['quantity'] * (1 if leg['action'] == 'BUY' else -1)
                for leg in legs
            )
        }

    @staticmethod
    def _match_pattern(legs: List[Dict], pattern: List[Dict]) -> bool:
        """檢查交易腿是否符合策略模式"""

        if len(legs) != len(pattern):
            return False

        # 檢查每個腿
        for i, (leg, pat) in enumerate(zip(legs, pattern)):
            # 檢查動作
            if leg['action'] != pat['action']:
                return False

            # 檢查選擇權類型
            if leg['option_type'] != pat['option_type']:
                return False

            # 檢查履約價關係
            if 'strike' in pat:
                if pat['strike'] == 'same':
                    # 所有履約價應相同
                    if i > 0 and leg['strike'] != legs[0]['strike']:
                        return False
                elif pat['strike'] == 'lower' and i > 0:
                    if leg['strike'] >= legs[i-1]['strike']:
                        return False
                elif pat['strike'] == 'higher' and i > 0:
                    if leg['strike'] <= legs[i-1]['strike']:
                        return False

        return True

    @staticmethod
    def format_strategy_summary(strategy: Dict) -> str:
        """格式化策略摘要文字"""

        summary = f"**{strategy['strategy_name']}**\n"
        summary += f"標的：{strategy['underlying']}\n"
        summary += f"說明：{strategy['description']}\n"
        summary += f"建立時間：{strategy['datetime']}\n"
        summary += f"到期日：{strategy['expiry']}\n"
        summary += f"總成本：${strategy['total_cost']:.2f}\n\n"

        summary += "組成部位：\n"
        for i, leg in enumerate(strategy['legs'], 1):
            action_str = "買入" if leg['action'] == 'BUY' else "賣出"
            type_str = "Call" if leg['option_type'] == 'C' else "Put"
            summary += f"{i}. {action_str} {type_str} @ ${leg['strike']:.2f} x {leg['quantity']} 口（${leg['price']:.2f}/口）\n"

        return summary

    @staticmethod
    def synthesize_strategies_from_positions(trades: List[Dict], stock_positions: Dict[str, float] = None) -> List[Dict]:
        """
        從持倉資料合成策略視圖
        
        Args:
            trades: 交易記錄列表
            stock_positions: 股票持倉 {symbol: quantity}，如果為 None 則從 trades 計算
            
        Returns:
            按標的分組的策略列表
        """
        if not trades:
            return []
        
        df = pd.DataFrame(trades)
        
        # 如果沒有提供股票持倉，從交易記錄計算
        if stock_positions is None:
            stock_positions = {}
            stock_trades = df[df.get('instrument_type', pd.Series(['stock'] * len(df))) == 'stock']
            if len(stock_trades) > 0:
                for symbol in stock_trades['symbol'].unique():
                    sym_trades = stock_trades[stock_trades['symbol'] == symbol]
                    qty = 0
                    for _, t in sym_trades.iterrows():
                        if t['action'].upper() in ['BUY', 'BOT']:
                            qty += t['quantity']
                        else:
                            qty -= t['quantity']
                    if qty > 0:
                        stock_positions[symbol] = qty
        
        # 獲取選擇權持倉
        option_trades = df[df.get('instrument_type', pd.Series(['stock'] * len(df))) == 'option']
        
        strategies = []
        
        # 按標的分組分析
        all_symbols = set()
        
        # 從股票持倉中獲取標的
        for sym in stock_positions.keys():
            all_symbols.add(sym)
        
        # 從選擇權交易中獲取標的
        if len(option_trades) > 0 and 'underlying' in option_trades.columns:
            for underlying in option_trades['underlying'].unique():
                if underlying:
                    all_symbols.add(underlying)
        
        for underlying in all_symbols:
            strategy_info = {
                'underlying': underlying,
                'has_stock': underlying in stock_positions,
                'stock_quantity': stock_positions.get(underlying, 0),
                'options': [],
                'strategy_type': None,
                'strategy_name': None,
                'description': None
            }
            
            # 獲取該標的的選擇權
            if len(option_trades) > 0 and 'underlying' in option_trades.columns:
                underlying_options = option_trades[option_trades['underlying'] == underlying]
                
                # 計算每個選擇權合約的淨持倉
                option_positions = {}
                for _, opt in underlying_options.iterrows():
                    key = (opt.get('strike'), opt.get('expiry'), opt.get('option_type'))
                    if key not in option_positions:
                        option_positions[key] = {
                            'strike': opt.get('strike'),
                            'expiry': opt.get('expiry'),
                            'option_type': opt.get('option_type'),
                            'quantity': 0,
                            'symbol': opt.get('symbol')
                        }
                    
                    if opt['action'].upper() in ['BUY', 'BOT']:
                        option_positions[key]['quantity'] += opt['quantity']
                    else:
                        option_positions[key]['quantity'] -= opt['quantity']
                
                # 只保留有持倉的選擇權
                for key, pos in option_positions.items():
                    if pos['quantity'] != 0:
                        strategy_info['options'].append({
                            'strike': pos['strike'],
                            'expiry': pos['expiry'],
                            'option_type': pos['option_type'],
                            'quantity': pos['quantity'],
                            'action': 'LONG' if pos['quantity'] > 0 else 'SHORT',
                            'symbol': pos['symbol']
                        })
            
            # 識別策略類型
            strategy_info = OptionStrategyDetector._identify_combined_strategy(strategy_info)
            
            if strategy_info['strategy_type']:
                strategies.append(strategy_info)
        
        return strategies
    
    @staticmethod
    def _identify_combined_strategy(strategy_info: Dict) -> Dict:
        """識別包含正股的組合策略"""
        
        has_stock = strategy_info['has_stock']
        options = strategy_info['options']
        
        if not options and not has_stock:
            return strategy_info
        
        # 分析選擇權持倉
        long_calls = [o for o in options if o['option_type'] == 'C' and o['action'] == 'LONG']
        short_calls = [o for o in options if o['option_type'] == 'C' and o['action'] == 'SHORT']
        long_puts = [o for o in options if o['option_type'] == 'P' and o['action'] == 'LONG']
        short_puts = [o for o in options if o['option_type'] == 'P' and o['action'] == 'SHORT']
        
        # 識別策略
        if has_stock:
            if short_calls and long_puts:
                # 正股 + Sell Call + Buy Put = Collar
                strategy_info['strategy_type'] = 'collar'
                strategy_info['strategy_name'] = 'Collar（領口策略）'
                strategy_info['description'] = '持有正股，賣出 Call 收取權利金，買入 Put 保護下檔'
            elif short_calls and not long_puts:
                # 正股 + Sell Call = Covered Call
                strategy_info['strategy_type'] = 'covered_call'
                strategy_info['strategy_name'] = 'Covered Call（備兌看漲）'
                strategy_info['description'] = '持有正股並賣出 Call 收取權利金'
            elif long_puts and not short_calls:
                # 正股 + Buy Put = Protective Put
                strategy_info['strategy_type'] = 'protective_put'
                strategy_info['strategy_name'] = 'Protective Put（保護性賣權）'
                strategy_info['description'] = '持有正股並買入 Put 保護下檔風險'
            elif short_puts:
                # 正股 + Sell Put = 額外加倉意圖
                strategy_info['strategy_type'] = 'stock_with_short_put'
                strategy_info['strategy_name'] = 'Stock + Short Put（持股賣權）'
                strategy_info['description'] = '持有正股並賣出 Put，願意在更低價格加碼'
            else:
                strategy_info['strategy_type'] = 'stock_only'
                strategy_info['strategy_name'] = '純股票持倉'
                strategy_info['description'] = '持有正股，無選擇權保護'
        else:
            # 純選擇權策略
            if long_calls and short_puts and not long_puts and not short_calls:
                strategy_info['strategy_type'] = 'synthetic_long'
                strategy_info['strategy_name'] = 'Synthetic Long（合成多頭）'
                strategy_info['description'] = '買 Call + 賣 Put，合成正股多頭'
            elif short_calls and long_puts and not long_calls and not short_puts:
                strategy_info['strategy_type'] = 'synthetic_short'
                strategy_info['strategy_name'] = 'Synthetic Short（合成空頭）'
                strategy_info['description'] = '賣 Call + 買 Put，合成正股空頭'
            elif long_calls and long_puts:
                if len(long_calls) == 1 and len(long_puts) == 1:
                    if long_calls[0]['strike'] == long_puts[0]['strike']:
                        strategy_info['strategy_type'] = 'long_straddle'
                        strategy_info['strategy_name'] = 'Long Straddle（買入跨式）'
                        strategy_info['description'] = '同履約價買 Call + Put，賭大幅波動'
                    else:
                        strategy_info['strategy_type'] = 'long_strangle'
                        strategy_info['strategy_name'] = 'Long Strangle（買入勒式）'
                        strategy_info['description'] = '不同履約價買 Call + Put，賭大幅波動'
            elif short_calls and short_puts:
                if len(short_calls) == 1 and len(short_puts) == 1:
                    if short_calls[0]['strike'] == short_puts[0]['strike']:
                        strategy_info['strategy_type'] = 'short_straddle'
                        strategy_info['strategy_name'] = 'Short Straddle（賣出跨式）'
                        strategy_info['description'] = '同履約價賣 Call + Put，收取權利金'
                    else:
                        strategy_info['strategy_type'] = 'short_strangle'
                        strategy_info['strategy_name'] = 'Short Strangle（賣出勒式）'
                        strategy_info['description'] = '不同履約價賣 Call + Put，收取權利金'
            elif long_puts and not long_calls and not short_calls and not short_puts:
                strategy_info['strategy_type'] = 'long_put'
                strategy_info['strategy_name'] = 'Long Put（買入賣權）'
                strategy_info['description'] = '看跌或避險'
            elif short_puts and not long_calls and not short_calls and not long_puts:
                strategy_info['strategy_type'] = 'short_put'
                strategy_info['strategy_name'] = 'Short Put（賣出賣權）'
                strategy_info['description'] = '看不跌或願意接股'
            elif long_calls and not long_puts and not short_calls and not short_puts:
                strategy_info['strategy_type'] = 'long_call'
                strategy_info['strategy_name'] = 'Long Call（買入買權）'
                strategy_info['description'] = '看漲'
            elif short_calls and not long_calls and not long_puts and not short_puts:
                strategy_info['strategy_type'] = 'naked_call'
                strategy_info['strategy_name'] = 'Naked Call（裸賣買權）'
                strategy_info['description'] = '高風險：賣出 Call 無正股覆蓋'
            else:
                strategy_info['strategy_type'] = 'complex'
                strategy_info['strategy_name'] = '複合策略'
                strategy_info['description'] = f'包含 {len(options)} 個選擇權部位'
        
        return strategy_info
