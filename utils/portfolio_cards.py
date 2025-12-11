"""
整合式持倉卡片模組

以 underlying 為主體，整合顯示正股+選擇權組合
自動識別策略類型（Covered Call, Protective Put 等）
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import yfinance as yf

from config.theme import COLORS
from utils.derivatives_support import InstrumentParser


@dataclass
class OptionPosition:
    """選擇權持倉"""
    symbol: str
    option_type: str  # 'Call' or 'Put'
    strike: float
    expiry: str
    quantity: int  # 正數=買入, 負數=賣出
    avg_cost: float = 0.0
    current_price: float = 0.0


@dataclass
class PortfolioPosition:
    """整合式持倉（正股+選擇權）"""
    underlying: str
    stock_quantity: float = 0.0
    stock_avg_cost: float = 0.0
    stock_current_price: float = 0.0
    options: List[OptionPosition] = None
    strategy_type: str = 'stock_only'
    strategy_name: str = '純股票持倉'
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    last_trade_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = []


class StrategyIdentifier:
    """策略識別器 - 支援 30+ 種選擇權策略"""
    
    @staticmethod
    def _count_options(pos, opt_type=None, direction=None):
        """計算選擇權數量"""
        count = 0
        for o in pos.options:
            if opt_type and o.option_type != opt_type:
                continue
            if direction == 'long' and o.quantity <= 0:
                continue
            if direction == 'short' and o.quantity >= 0:
                continue
            count += 1
        return count
    
    @staticmethod
    def _get_strikes(pos, opt_type=None, direction=None):
        """取得履約價列表"""
        strikes = []
        for o in pos.options:
            if opt_type and o.option_type != opt_type:
                continue
            if direction == 'long' and o.quantity <= 0:
                continue
            if direction == 'short' and o.quantity >= 0:
                continue
            strikes.append(o.strike)
        return sorted(strikes)
    
    STRATEGY_DEFINITIONS = {
        # ========== 正股 + 選擇權組合 ==========
        'collar': {
            'name': 'Collar',
            'name_zh': '領口策略',
            'description': '持有正股 + 買 Put + 賣 Call，鎖定風險區間',
            'color': '#8B5CF6',
            'conditions': lambda pos: (
                pos.stock_quantity > 0 and
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options)
            )
        },
        'covered_call': {
            'name': 'Covered Call',
            'name_zh': '備兌看漲',
            'description': '持有正股，賣出看漲期權收取權利金',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity > 0 and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                not any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options)
            )
        },
        'protective_put': {
            'name': 'Protective Put',
            'name_zh': '保護性看跌',
            'description': '持有正股，買入看跌期權保護下檔',
            'color': '#3B82F6',
            'conditions': lambda pos: (
                pos.stock_quantity > 0 and
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                not any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options)
            )
        },
        'covered_strangle': {
            'name': 'Covered Strangle',
            'name_zh': '備兌勒式',
            'description': '持有正股 + 賣 Call + 賣 Put，雙向收取權利金',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity > 0 and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options)
            )
        },
        
        # ========== 價差策略 (Spreads) ==========
        'bull_call_spread': {
            'name': 'Bull Call Spread',
            'name_zh': '牛市看漲價差',
            'description': '買低履約價 Call + 賣高履約價 Call，看漲但限制風險',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Call', 'short') >= 1 and
                not any(o.option_type == 'Put' for o in pos.options) and
                min(StrategyIdentifier._get_strikes(pos, 'Call', 'long') or [999]) < 
                min(StrategyIdentifier._get_strikes(pos, 'Call', 'short') or [0])
            )
        },
        'bear_call_spread': {
            'name': 'Bear Call Spread',
            'name_zh': '熊市看漲價差',
            'description': '賣低履約價 Call + 買高履約價 Call，看跌收取權利金',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Call', 'short') >= 1 and
                not any(o.option_type == 'Put' for o in pos.options) and
                min(StrategyIdentifier._get_strikes(pos, 'Call', 'short') or [999]) < 
                min(StrategyIdentifier._get_strikes(pos, 'Call', 'long') or [0])
            )
        },
        'bull_put_spread': {
            'name': 'Bull Put Spread',
            'name_zh': '牛市看跌價差',
            'description': '賣高履約價 Put + 買低履約價 Put，看漲收取權利金',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Put', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'short') >= 1 and
                not any(o.option_type == 'Call' for o in pos.options) and
                max(StrategyIdentifier._get_strikes(pos, 'Put', 'short') or [0]) > 
                max(StrategyIdentifier._get_strikes(pos, 'Put', 'long') or [999])
            )
        },
        'bear_put_spread': {
            'name': 'Bear Put Spread',
            'name_zh': '熊市看跌價差',
            'description': '買高履約價 Put + 賣低履約價 Put，看跌但限制風險',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Put', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'short') >= 1 and
                not any(o.option_type == 'Call' for o in pos.options) and
                max(StrategyIdentifier._get_strikes(pos, 'Put', 'long') or [0]) > 
                max(StrategyIdentifier._get_strikes(pos, 'Put', 'short') or [999])
            )
        },
        'put_spread': {
            'name': 'Put Spread',
            'name_zh': 'Put 價差',
            'description': '買賣不同履約價的 Put，限制風險與獲利',
            'color': '#8B5CF6',
            'conditions': lambda pos: pos.stock_quantity == 0 and (
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options) and
                not any(o.option_type == 'Call' for o in pos.options)
            )
        },
        'call_spread': {
            'name': 'Call Spread',
            'name_zh': 'Call 價差',
            'description': '買賣不同履約價的 Call，限制風險與獲利',
            'color': '#8B5CF6',
            'conditions': lambda pos: pos.stock_quantity == 0 and (
                any(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                not any(o.option_type == 'Put' for o in pos.options)
            )
        },
        
        # ========== 跨式/勒式策略 (Straddle/Strangle) ==========
        'long_straddle': {
            'name': 'Long Straddle',
            'name_zh': '買入跨式',
            'description': '同時買入相同履約價的 Call 和 Put，預期大幅波動',
            'color': '#6366F1',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                not any(o.quantity < 0 for o in pos.options) and
                len(set(o.strike for o in pos.options)) == 1  # 相同履約價
            )
        },
        'short_straddle': {
            'name': 'Short Straddle',
            'name_zh': '賣出跨式',
            'description': '同時賣出相同履約價的 Call 和 Put，預期盤整',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options) and
                not any(o.quantity > 0 for o in pos.options) and
                len(set(o.strike for o in pos.options)) == 1
            )
        },
        'long_strangle': {
            'name': 'Long Strangle',
            'name_zh': '買入勒式',
            'description': '買入不同履約價的 Call 和 Put，預期大幅波動',
            'color': '#6366F1',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                not any(o.quantity < 0 for o in pos.options) and
                len(set(o.strike for o in pos.options)) > 1
            )
        },
        'short_strangle': {
            'name': 'Short Strangle',
            'name_zh': '賣出勒式',
            'description': '賣出不同履約價的 Call 和 Put，預期盤整收取權利金',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options) and
                not any(o.quantity > 0 for o in pos.options) and
                len(set(o.strike for o in pos.options)) > 1
            )
        },
        
        # ========== 蝶式/鐵蝶式 (Butterfly) ==========
        'iron_butterfly': {
            'name': 'Iron Butterfly',
            'name_zh': '鐵蝶式',
            'description': '賣出跨式 + 買入勒式保護，預期盤整',
            'color': '#EC4899',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Call', 'short') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'short') >= 1 and
                len(pos.options) == 4
            )
        },
        'iron_condor': {
            'name': 'Iron Condor',
            'name_zh': '鐵禿鷹',
            'description': '賣出勒式 + 買入更遠履約價保護，預期區間盤整',
            'color': '#EC4899',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Call', 'short') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'long') >= 1 and
                StrategyIdentifier._count_options(pos, 'Put', 'short') >= 1 and
                len(set(o.strike for o in pos.options)) >= 4
            )
        },
        
        # ========== 比率策略 (Ratio) ==========
        'call_ratio_spread': {
            'name': 'Call Ratio Spread',
            'name_zh': 'Call 比率價差',
            'description': '買入 Call + 賣出更多 Call，降低成本但增加風險',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'short') > 
                StrategyIdentifier._count_options(pos, 'Call', 'long') > 0 and
                not any(o.option_type == 'Put' for o in pos.options)
            )
        },
        'put_ratio_spread': {
            'name': 'Put Ratio Spread',
            'name_zh': 'Put 比率價差',
            'description': '買入 Put + 賣出更多 Put，降低成本但增加風險',
            'color': '#F59E0B',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Put', 'short') > 
                StrategyIdentifier._count_options(pos, 'Put', 'long') > 0 and
                not any(o.option_type == 'Call' for o in pos.options)
            )
        },
        'call_ratio_backspread': {
            'name': 'Call Ratio Backspread',
            'name_zh': 'Call 反向比率',
            'description': '賣出 Call + 買入更多 Call，看大漲',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Call', 'long') > 
                StrategyIdentifier._count_options(pos, 'Call', 'short') > 0 and
                not any(o.option_type == 'Put' for o in pos.options)
            )
        },
        'put_ratio_backspread': {
            'name': 'Put Ratio Backspread',
            'name_zh': 'Put 反向比率',
            'description': '賣出 Put + 買入更多 Put，看大跌',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                StrategyIdentifier._count_options(pos, 'Put', 'long') > 
                StrategyIdentifier._count_options(pos, 'Put', 'short') > 0 and
                not any(o.option_type == 'Call' for o in pos.options)
            )
        },
        
        # ========== 合成策略 (Synthetic) ==========
        'synthetic_long': {
            'name': 'Synthetic Long',
            'name_zh': '合成多頭',
            'description': '買 Call + 賣 Put 同履約價，模擬持有正股',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options) and
                not any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                not any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options)
            )
        },
        'synthetic_short': {
            'name': 'Synthetic Short',
            'name_zh': '合成空頭',
            'description': '賣 Call + 買 Put 同履約價，模擬放空正股',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                any(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                any(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                not any(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                not any(o.option_type == 'Put' and o.quantity < 0 for o in pos.options)
            )
        },
        
        # ========== 單腳策略 ==========
        'cash_secured_put': {
            'name': 'Cash Secured Put',
            'name_zh': '現金擔保看跌',
            'description': '賣出看跌期權，準備接貨',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                all(o.option_type == 'Put' and o.quantity < 0 for o in pos.options) and
                len(pos.options) > 0
            )
        },
        'naked_call': {
            'name': 'Naked Call',
            'name_zh': '裸賣看漲',
            'description': '賣出看漲期權，風險無限',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                all(o.option_type == 'Call' and o.quantity < 0 for o in pos.options) and
                len(pos.options) > 0
            )
        },
        'long_call': {
            'name': 'Long Call',
            'name_zh': '買入看漲',
            'description': '看多標的，買入看漲期權',
            'color': '#10B981',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                all(o.option_type == 'Call' and o.quantity > 0 for o in pos.options) and
                len(pos.options) > 0
            )
        },
        'long_put': {
            'name': 'Long Put',
            'name_zh': '買入看跌',
            'description': '看空標的或對沖，買入看跌期權',
            'color': '#EF4444',
            'conditions': lambda pos: (
                pos.stock_quantity == 0 and
                all(o.option_type == 'Put' and o.quantity > 0 for o in pos.options) and
                len(pos.options) > 0
            )
        },
        
        # ========== 通用分類 ==========
        'stock_with_options': {
            'name': 'Stock + Options',
            'name_zh': '複合策略',
            'description': '持有正股與多個選擇權部位',
            'color': '#6366F1',
            'conditions': lambda pos: pos.stock_quantity > 0 and len(pos.options) > 0
        },
        'options_only': {
            'name': 'Options Only',
            'name_zh': '純選擇權',
            'description': '僅持有選擇權部位',
            'color': '#EC4899',
            'conditions': lambda pos: pos.stock_quantity == 0 and len(pos.options) > 0
        },
        'stock_only': {
            'name': 'Stock Only',
            'name_zh': '純股票持倉',
            'description': '持有正股，無選擇權保護',
            'color': '#6B7280',
            'conditions': lambda pos: pos.stock_quantity > 0 and len(pos.options) == 0
        },
    }
    
    @classmethod
    def identify(cls, position: PortfolioPosition) -> tuple:
        """
        識別持倉策略類型
        
        Returns:
            (strategy_type, strategy_name, description, color)
        """
        # 按優先順序檢查（複雜策略優先，通用分類最後）
        priority_order = [
            # 正股 + 選擇權組合
            'collar', 'covered_strangle', 'covered_call', 'protective_put',
            # 四腳策略
            'iron_condor', 'iron_butterfly',
            # 價差策略（方向性）
            'bull_call_spread', 'bear_call_spread', 'bull_put_spread', 'bear_put_spread',
            # 價差策略（通用）
            'call_spread', 'put_spread',
            # 跨式/勒式
            'long_straddle', 'short_straddle', 'long_strangle', 'short_strangle',
            # 比率策略
            'call_ratio_spread', 'put_ratio_spread', 'call_ratio_backspread', 'put_ratio_backspread',
            # 合成策略
            'synthetic_long', 'synthetic_short',
            # 單腳策略
            'cash_secured_put', 'naked_call', 'long_call', 'long_put',
            # 通用分類
            'stock_with_options', 'options_only', 'stock_only'
        ]
        
        for strategy_type in priority_order:
            definition = cls.STRATEGY_DEFINITIONS[strategy_type]
            if definition['conditions'](position):
                return (
                    strategy_type,
                    definition['name_zh'],
                    definition['description'],
                    definition['color']
                )
        
        return ('unknown', '未識別', '', '#6B7280')


class PortfolioAnalyzer:
    """投資組合分析器"""
    
    @staticmethod
    def build_positions_from_trades(trades: List[Dict]) -> Dict[str, PortfolioPosition]:
        """
        從交易記錄建立整合式持倉
        
        Args:
            trades: 交易記錄列表
            
        Returns:
            Dict[underlying, PortfolioPosition]
        """
        positions = {}
        parser = InstrumentParser()
        
        for trade in trades:
            symbol = trade['symbol']
            parsed = parser.parse_symbol(symbol)
            underlying = parsed['underlying']
            
            # 初始化持倉
            if underlying not in positions:
                positions[underlying] = PortfolioPosition(underlying=underlying)
            
            pos = positions[underlying]
            
            # 計算數量
            # 注意：資料庫中的 quantity 可能已經是負數（SELL 時）
            # 所以我們需要檢查 quantity 的符號，而不是 action
            qty = trade['quantity']
            # 如果 quantity 已經是負數，表示是賣出，不需要再取負
            # 如果 quantity 是正數但 action 是 SELL，則取負
            if qty > 0 and trade['action'].upper() in ['SELL', 'SLD']:
                qty = -qty
            
            # 更新最後交易日期
            try:
                trade_date = pd.to_datetime(trade['datetime'])
                if pos.last_trade_date is None or trade_date > pos.last_trade_date:
                    pos.last_trade_date = trade_date
            except:
                pass
            
            # 累計已實現損益
            pos.realized_pnl += trade.get('realized_pnl', 0)
            
            if parsed['instrument_type'] == 'stock':
                # 正股
                if qty > 0:
                    # 買入：更新平均成本
                    total_cost = pos.stock_avg_cost * pos.stock_quantity + trade['price'] * qty
                    pos.stock_quantity += qty
                    if pos.stock_quantity > 0:
                        pos.stock_avg_cost = total_cost / pos.stock_quantity
                else:
                    # 賣出
                    pos.stock_quantity += qty  # qty 是負數
                    
            elif parsed['instrument_type'] == 'option':
                # 選擇權
                # 查找是否已有相同的選擇權部位
                existing_opt = None
                for opt in pos.options:
                    if (opt.strike == parsed['strike'] and 
                        opt.expiry == parsed['expiry'] and
                        opt.option_type == parsed['option_type']):
                        existing_opt = opt
                        break
                
                if existing_opt:
                    existing_opt.quantity += int(qty)
                    # 移除數量為 0 的部位
                    if existing_opt.quantity == 0:
                        pos.options.remove(existing_opt)
                else:
                    if qty != 0:
                        pos.options.append(OptionPosition(
                            symbol=symbol,
                            option_type=parsed['option_type'],
                            strike=parsed['strike'],
                            expiry=parsed['expiry'],
                            quantity=int(qty),
                            avg_cost=trade['price']
                        ))
        
        # 識別策略類型
        for underlying, pos in positions.items():
            strategy_type, strategy_name, description, color = StrategyIdentifier.identify(pos)
            pos.strategy_type = strategy_type
            pos.strategy_name = strategy_name
        
        # 過濾掉沒有持倉的標的
        positions = {k: v for k, v in positions.items() 
                     if v.stock_quantity > 0 or len(v.options) > 0}
        
        return positions
    
    @staticmethod
    def fetch_current_prices(positions: Dict[str, PortfolioPosition]) -> None:
        """
        取得即時價格並更新持倉
        """
        for underlying, pos in positions.items():
            try:
                ticker = yf.Ticker(underlying)
                hist = ticker.history(period="1d")
                if len(hist) > 0:
                    pos.stock_current_price = hist['Close'].iloc[-1]
                    
                    # 計算未實現損益
                    if pos.stock_quantity > 0:
                        market_value = pos.stock_current_price * pos.stock_quantity
                        cost_basis = pos.stock_avg_cost * pos.stock_quantity
                        pos.unrealized_pnl = market_value - cost_basis
            except:
                pass


def render_portfolio_card(pos: PortfolioPosition, pnl_by_symbol: Dict[str, float] = None):
    """
    渲染整合式持倉卡片
    
    Args:
        pos: PortfolioPosition 物件
        pnl_by_symbol: 各標的已實現損益（可選）
    """
    strategy_def = StrategyIdentifier.STRATEGY_DEFINITIONS.get(
        pos.strategy_type, 
        {'color': '#6B7280', 'name_zh': '未識別', 'description': ''}
    )
    badge_color = strategy_def['color']
    
    with st.container(border=True):
        # 標題區域：標的 + 策略標籤
        col_title, col_badge = st.columns([2, 1])
        
        with col_title:
            st.markdown(f"**{pos.underlying}**")
        
        with col_badge:
            st.markdown(f"""
            <span style="background: {badge_color}; color: #fff; padding: 2px 8px; 
                         border-radius: 4px; font-size: 0.7rem;">
                {pos.strategy_name}
            </span>
            """, unsafe_allow_html=True)
        
        # 策略說明
        st.caption(strategy_def.get('description', ''))
        
        # 正股持倉
        if pos.stock_quantity > 0:
            # 價格資訊
            if pos.stock_current_price > 0:
                price_str = f"${pos.stock_current_price:.2f}"
                market_value = pos.stock_current_price * pos.stock_quantity
                
                # 未實現損益
                unrealized_color = COLORS.PROFIT if pos.unrealized_pnl >= 0 else COLORS.LOSS
                unrealized_pct = (pos.unrealized_pnl / (pos.stock_avg_cost * pos.stock_quantity) * 100) if pos.stock_avg_cost > 0 else 0
                
                st.markdown(f"""
                <div style="font-size: 0.85rem;">
                    <span style="color: {COLORS.TEXT_SECONDARY};">現價:</span>
                    <span style="color: {COLORS.TEXT_PRIMARY}; font-weight: 600;">{price_str}</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="font-size: 0.85rem; margin-top: 0.3rem;">
                    📈 <span style="color: {COLORS.TEXT_PRIMARY};">正股: {pos.stock_quantity:,.0f} 股</span>
                    <span style="color: {COLORS.TEXT_MUTED};">(${market_value:,.0f})</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="font-size: 0.85rem;">
                    <span style="color: {COLORS.TEXT_SECONDARY};">未實現:</span>
                    <span style="color: {unrealized_color}; font-weight: 500;">
                        ${pos.unrealized_pnl:+,.0f} ({unrealized_pct:+.1f}%)
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"📈 **正股**: {pos.stock_quantity:,.0f} 股")
        
        # 選擇權持倉
        for opt in pos.options:
            action_icon = "🟢" if opt.quantity > 0 else "🔴"
            action_text = "買" if opt.quantity > 0 else "賣"
            opt_type = opt.option_type
            
            # 格式化到期日
            expiry_str = str(opt.expiry).replace('-', '/')
            
            st.markdown(f"""
            <div style="font-size: 0.85rem; margin-top: 0.2rem;">
                {action_icon} <b>{action_text} {opt_type}</b> @ ${opt.strike:.0f} x {abs(opt.quantity)} 
                <span style="color: {COLORS.TEXT_MUTED};">(到期: {expiry_str})</span>
            </div>
            """, unsafe_allow_html=True)
        
        # 已實現損益
        if pos.realized_pnl != 0:
            realized_color = COLORS.PROFIT if pos.realized_pnl >= 0 else COLORS.LOSS
            st.markdown(f"""
            <div style="font-size: 0.9rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid {COLORS.BORDER_MUTED};">
                <span style="color: {COLORS.TEXT_SECONDARY};">已實現:</span>
                <span style="color: {realized_color}; font-weight: 600;">
                    ${pos.realized_pnl:,.2f}
                </span>
            </div>
            """, unsafe_allow_html=True)


def render_portfolio_overview(trades: List[Dict], pnl_by_symbol: Dict[str, float] = None):
    """
    渲染整合式持倉總覽
    
    Args:
        trades: 交易記錄列表
        pnl_by_symbol: 各標的已實現損益
    """
    # 建立整合式持倉
    positions = PortfolioAnalyzer.build_positions_from_trades(trades)
    
    if not positions:
        st.info("目前無持倉")
        return
    
    # 取得即時價格
    with st.spinner("取得即時價格..."):
        PortfolioAnalyzer.fetch_current_prices(positions)
    
    # 按策略類型分組
    strategy_groups = {}
    for underlying, pos in positions.items():
        strategy_type = pos.strategy_type
        if strategy_type not in strategy_groups:
            strategy_groups[strategy_type] = []
        strategy_groups[strategy_type].append(pos)
    
    # 渲染卡片（3 欄佈局）
    all_positions = list(positions.values())
    
    # 按最後交易日期排序
    all_positions.sort(key=lambda x: x.last_trade_date or datetime.min, reverse=True)
    
    # 渲染
    cols = st.columns(3)
    for idx, pos in enumerate(all_positions):
        with cols[idx % 3]:
            render_portfolio_card(pos, pnl_by_symbol)
