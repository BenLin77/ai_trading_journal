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
