"""
選擇權策略識別模組

支援策略類型：
1. 基本策略：Long/Short Call/Put
2. 垂直價差：Bull Call Spread, Bear Put Spread, Bull Put Spread, Bear Call Spread
3. 備兌策略：Covered Call, Protective Put, Collar
4. 跨式策略：Straddle, Strangle
5. 鐵系策略：Iron Condor, Iron Butterfly
6. 蝴蝶策略：Butterfly Spread, Broken Wing Butterfly
7. 進階策略：ZEBRA, PMCC (Poor Man's Covered Call), Jade Lizard, Ratio Spread
8. 複合策略：Calendar Spread, Diagonal Spread
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class StrategyType(Enum):
    # 基本策略
    LONG_CALL = "純看漲"
    SHORT_CALL = "賣出看漲"
    LONG_PUT = "純看跌"
    SHORT_PUT = "賣出看跌"
    
    # 股票 + 選擇權
    COVERED_CALL = "備兌看漲"
    PROTECTIVE_PUT = "保護性賣權"
    COLLAR = "領口策略"
    MARRIED_PUT = "婚姻賣權"
    
    # 垂直價差
    BULL_CALL_SPREAD = "牛市看漲價差"
    BEAR_CALL_SPREAD = "熊市看漲價差"
    BULL_PUT_SPREAD = "牛市看跌價差"
    BEAR_PUT_SPREAD = "熊市看跌價差"
    
    # 跨式策略
    LONG_STRADDLE = "買入跨式"
    SHORT_STRADDLE = "賣出跨式"
    LONG_STRANGLE = "買入勒式"
    SHORT_STRANGLE = "賣出勒式"
    
    # 鐵系策略
    IRON_CONDOR = "鐵禿鷹"
    IRON_BUTTERFLY = "鐵蝴蝶"
    
    # 蝴蝶策略
    CALL_BUTTERFLY = "看漲蝴蝶"
    PUT_BUTTERFLY = "看跌蝴蝶"
    BROKEN_WING_BUTTERFLY = "斷翅蝴蝶"
    
    # 進階策略
    ZEBRA_CALL = "ZEBRA 看漲"  # Zero Extrinsic Back Ratio
    ZEBRA_PUT = "ZEBRA 看跌"
    PMCC = "窮人備兌"  # Poor Man's Covered Call
    JADE_LIZARD = "翡翠蜥蜴"
    RATIO_CALL_SPREAD = "比率看漲價差"
    RATIO_PUT_SPREAD = "比率看跌價差"
    
    # 時間價差
    CALENDAR_SPREAD = "日曆價差"
    DIAGONAL_SPREAD = "對角價差"
    
    # 複合策略
    RISK_REVERSAL = "風險反轉"
    SYNTHETIC_LONG = "合成多頭"
    SYNTHETIC_SHORT = "合成空頭"
    
    # 純股票
    STOCK_ONLY = "純股票持倉"
    
    # 未識別
    CUSTOM = "自訂組合"
    UNKNOWN = "未知策略"


@dataclass
class OptionLeg:
    """選擇權腿"""
    symbol: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiry: str
    quantity: int  # 正數=買入, 負數=賣出
    premium: float = 0.0
    
    @property
    def is_long(self) -> bool:
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        return self.quantity < 0
    
    @property
    def is_call(self) -> bool:
        return self.option_type.lower() == 'call'
    
    @property
    def is_put(self) -> bool:
        return self.option_type.lower() == 'put'


@dataclass
class StockPosition:
    """股票持倉"""
    symbol: str
    quantity: int  # 正數=多頭, 負數=空頭
    avg_cost: float
    current_price: float = 0.0


@dataclass
class StrategyResult:
    """策略識別結果"""
    strategy_type: StrategyType
    strategy_name: str
    description: str
    risk_profile: str  # 'limited', 'unlimited', 'defined'
    max_profit: str
    max_loss: str
    breakeven: List[float]
    greeks_summary: Dict[str, float]
    legs: List[OptionLeg]
    stock: Optional[StockPosition]
    confidence: float  # 0-1 識別信心度


class OptionStrategyDetector:
    """選擇權策略識別器"""
    
    # 策略描述
    STRATEGY_DESCRIPTIONS = {
        StrategyType.LONG_CALL: "買入看漲期權，看漲標的，風險有限，獲利無限",
        StrategyType.SHORT_CALL: "賣出看漲期權，收取權利金，風險無限",
        StrategyType.LONG_PUT: "買入看跌期權，看跌標的或避險，風險有限",
        StrategyType.SHORT_PUT: "賣出看跌期權，收取權利金，願意接股",
        
        StrategyType.COVERED_CALL: "持有正股，賣出看漲期權收取權利金，限制上漲獲利",
        StrategyType.PROTECTIVE_PUT: "持有正股，買入看跌期權保護下跌風險",
        StrategyType.COLLAR: "持有正股 + 買 Put + 賣 Call，鎖定風險區間",
        StrategyType.MARRIED_PUT: "同時買入股票和看跌期權，限制下跌風險",
        
        StrategyType.BULL_CALL_SPREAD: "買低履約價 Call + 賣高履約價 Call，看漲但限制風險",
        StrategyType.BEAR_CALL_SPREAD: "賣低履約價 Call + 買高履約價 Call，看跌收取權利金",
        StrategyType.BULL_PUT_SPREAD: "賣高履約價 Put + 買低履約價 Put，看漲收取權利金",
        StrategyType.BEAR_PUT_SPREAD: "買高履約價 Put + 賣低履約價 Put，看跌但限制風險",
        
        StrategyType.LONG_STRADDLE: "同時買入相同履約價的 Call 和 Put，預期大幅波動",
        StrategyType.SHORT_STRADDLE: "同時賣出相同履約價的 Call 和 Put，預期小幅波動",
        StrategyType.LONG_STRANGLE: "買入不同履約價的 Call 和 Put，預期大幅波動",
        StrategyType.SHORT_STRANGLE: "賣出不同履約價的 Call 和 Put，預期小幅波動",
        
        StrategyType.IRON_CONDOR: "賣出價外 Put Spread + 賣出價外 Call Spread，預期區間盤整",
        StrategyType.IRON_BUTTERFLY: "賣出 ATM Straddle + 買入 OTM Strangle，預期小幅波動",
        
        StrategyType.CALL_BUTTERFLY: "買1低+賣2中+買1高履約價 Call，預期小幅波動",
        StrategyType.PUT_BUTTERFLY: "買1低+賣2中+買1高履約價 Put，預期小幅波動",
        StrategyType.BROKEN_WING_BUTTERFLY: "不對稱蝴蝶，一側風險較大但可收取權利金",
        
        StrategyType.ZEBRA_CALL: "買2個ITM Call + 賣1個ATM Call，模擬持股但資金效率高",
        StrategyType.ZEBRA_PUT: "買2個ITM Put + 賣1個ATM Put，模擬放空但資金效率高",
        StrategyType.PMCC: "買入長期深價內 Call + 賣出短期價外 Call，低成本備兌策略",
        StrategyType.JADE_LIZARD: "賣出 Put + 賣出 Call Spread，收取權利金無上行風險",
        StrategyType.RATIO_CALL_SPREAD: "買入 Call + 賣出更多 Call，部分看漲但限制成本",
        StrategyType.RATIO_PUT_SPREAD: "買入 Put + 賣出更多 Put，部分看跌但限制成本",
        
        StrategyType.CALENDAR_SPREAD: "賣出近期 + 買入遠期相同履約價，賺取時間價值差",
        StrategyType.DIAGONAL_SPREAD: "賣出近期 + 買入遠期不同履約價，結合方向和時間",
        
        StrategyType.RISK_REVERSAL: "賣出 Put + 買入 Call，合成多頭或避險",
        StrategyType.SYNTHETIC_LONG: "買入 ATM Call + 賣出 ATM Put，模擬持股",
        StrategyType.SYNTHETIC_SHORT: "賣出 ATM Call + 買入 ATM Put，模擬放空",
        
        StrategyType.STOCK_ONLY: "純股票持倉，無選擇權保護",
        StrategyType.CUSTOM: "自訂選擇權組合",
        StrategyType.UNKNOWN: "無法識別的策略組合",
    }
    
    @classmethod
    def detect_strategy(
        cls,
        options: List[OptionLeg],
        stock: Optional[StockPosition] = None,
        current_price: float = 0.0
    ) -> StrategyResult:
        """
        識別選擇權策略
        
        Args:
            options: 選擇權腿列表
            stock: 股票持倉（可選）
            current_price: 標的當前價格
            
        Returns:
            策略識別結果
        """
        if not options and not stock:
            return cls._create_result(StrategyType.UNKNOWN, [], None, 0.0)
        
        if not options and stock:
            return cls._create_result(StrategyType.STOCK_ONLY, [], stock, 1.0)
        
        # 分類選擇權
        long_calls = [o for o in options if o.is_call and o.is_long]
        short_calls = [o for o in options if o.is_call and o.is_short]
        long_puts = [o for o in options if o.is_put and o.is_long]
        short_puts = [o for o in options if o.is_put and o.is_short]
        
        has_stock = stock is not None and stock.quantity != 0
        is_long_stock = has_stock and stock.quantity > 0
        is_short_stock = has_stock and stock.quantity < 0
        
        # 計算總數量
        total_long_calls = sum(abs(o.quantity) for o in long_calls)
        total_short_calls = sum(abs(o.quantity) for o in short_calls)
        total_long_puts = sum(abs(o.quantity) for o in long_puts)
        total_short_puts = sum(abs(o.quantity) for o in short_puts)
        
        # ===== 股票 + 選擇權策略 =====
        if is_long_stock:
            # Covered Call: 持股 + 賣 Call
            if short_calls and not long_calls and not long_puts and not short_puts:
                return cls._create_result(StrategyType.COVERED_CALL, options, stock, 0.95)
            
            # Protective Put: 持股 + 買 Put
            if long_puts and not short_puts and not long_calls and not short_calls:
                return cls._create_result(StrategyType.PROTECTIVE_PUT, options, stock, 0.95)
            
            # Collar: 持股 + 買 Put + 賣 Call
            if long_puts and short_calls and not long_calls and not short_puts:
                return cls._create_result(StrategyType.COLLAR, options, stock, 0.95)
            
            # 備兌勒式: 持股 + 賣 Call + 賣 Put
            if short_calls and short_puts and not long_calls and not long_puts:
                return cls._create_result(StrategyType.SHORT_STRANGLE, options, stock, 0.8)
        
        # ===== 純選擇權策略 =====
        if not has_stock:
            # 單腿策略
            if len(options) == 1:
                opt = options[0]
                if opt.is_call and opt.is_long:
                    return cls._create_result(StrategyType.LONG_CALL, options, None, 1.0)
                elif opt.is_call and opt.is_short:
                    return cls._create_result(StrategyType.SHORT_CALL, options, None, 1.0)
                elif opt.is_put and opt.is_long:
                    return cls._create_result(StrategyType.LONG_PUT, options, None, 1.0)
                elif opt.is_put and opt.is_short:
                    return cls._create_result(StrategyType.SHORT_PUT, options, None, 1.0)
            
            # ZEBRA 策略: 買2個ITM + 賣1個ATM
            if len(long_calls) >= 1 and len(short_calls) >= 1:
                if total_long_calls == 2 * total_short_calls:
                    # 檢查是否 ITM/ATM 配置
                    long_strikes = [o.strike for o in long_calls]
                    short_strikes = [o.strike for o in short_calls]
                    if all(ls < ss for ls in long_strikes for ss in short_strikes):
                        return cls._create_result(StrategyType.ZEBRA_CALL, options, None, 0.85)
            
            if len(long_puts) >= 1 and len(short_puts) >= 1:
                if total_long_puts == 2 * total_short_puts:
                    long_strikes = [o.strike for o in long_puts]
                    short_strikes = [o.strike for o in short_puts]
                    if all(ls > ss for ls in long_strikes for ss in short_strikes):
                        return cls._create_result(StrategyType.ZEBRA_PUT, options, None, 0.85)
            
            # 垂直價差
            if len(options) == 2:
                # Bull Call Spread: 買低 Call + 賣高 Call
                if len(long_calls) == 1 and len(short_calls) == 1:
                    if long_calls[0].strike < short_calls[0].strike:
                        return cls._create_result(StrategyType.BULL_CALL_SPREAD, options, None, 0.95)
                    else:
                        return cls._create_result(StrategyType.BEAR_CALL_SPREAD, options, None, 0.95)
                
                # Put Spread
                if len(long_puts) == 1 and len(short_puts) == 1:
                    if long_puts[0].strike > short_puts[0].strike:
                        return cls._create_result(StrategyType.BEAR_PUT_SPREAD, options, None, 0.95)
                    else:
                        return cls._create_result(StrategyType.BULL_PUT_SPREAD, options, None, 0.95)
                
                # Straddle: 同履約價 Call + Put
                if len(long_calls) == 1 and len(long_puts) == 1:
                    if abs(long_calls[0].strike - long_puts[0].strike) < 0.01:
                        return cls._create_result(StrategyType.LONG_STRADDLE, options, None, 0.95)
                    else:
                        return cls._create_result(StrategyType.LONG_STRANGLE, options, None, 0.95)
                
                if len(short_calls) == 1 and len(short_puts) == 1:
                    if abs(short_calls[0].strike - short_puts[0].strike) < 0.01:
                        return cls._create_result(StrategyType.SHORT_STRADDLE, options, None, 0.95)
                    else:
                        return cls._create_result(StrategyType.SHORT_STRANGLE, options, None, 0.95)
                
                # Risk Reversal: 賣 Put + 買 Call
                if len(long_calls) == 1 and len(short_puts) == 1:
                    return cls._create_result(StrategyType.RISK_REVERSAL, options, None, 0.9)
                
                # Synthetic Long: 買 ATM Call + 賣 ATM Put
                if len(long_calls) == 1 and len(short_puts) == 1:
                    if abs(long_calls[0].strike - short_puts[0].strike) < 0.01:
                        return cls._create_result(StrategyType.SYNTHETIC_LONG, options, None, 0.9)
            
            # Iron Condor: 4腿，賣 Put Spread + 賣 Call Spread
            if len(options) == 4:
                if len(long_calls) == 1 and len(short_calls) == 1 and \
                   len(long_puts) == 1 and len(short_puts) == 1:
                    # 檢查是否為 Iron Condor 結構
                    put_strikes = sorted([long_puts[0].strike, short_puts[0].strike])
                    call_strikes = sorted([short_calls[0].strike, long_calls[0].strike])
                    
                    if put_strikes[1] < call_strikes[0]:  # Put spread 在 Call spread 下方
                        return cls._create_result(StrategyType.IRON_CONDOR, options, None, 0.95)
                    elif abs(put_strikes[1] - call_strikes[0]) < 0.01:  # 中間履約價相同
                        return cls._create_result(StrategyType.IRON_BUTTERFLY, options, None, 0.95)
            
            # Butterfly: 3個不同履約價，中間賣2個
            if len(options) == 3 or len(options) == 4:
                all_calls = long_calls + short_calls
                all_puts = long_puts + short_puts
                
                # Call Butterfly
                if len(all_calls) >= 3 and len(all_puts) == 0:
                    strikes = sorted(set(o.strike for o in all_calls))
                    if len(strikes) == 3:
                        return cls._create_result(StrategyType.CALL_BUTTERFLY, options, None, 0.85)
                
                # Put Butterfly
                if len(all_puts) >= 3 and len(all_calls) == 0:
                    strikes = sorted(set(o.strike for o in all_puts))
                    if len(strikes) == 3:
                        return cls._create_result(StrategyType.PUT_BUTTERFLY, options, None, 0.85)
            
            # Jade Lizard: 賣 Put + 賣 Call Spread (無上行風險)
            if len(short_puts) == 1 and len(short_calls) == 1 and len(long_calls) == 1:
                if short_calls[0].strike < long_calls[0].strike:
                    return cls._create_result(StrategyType.JADE_LIZARD, options, None, 0.85)
            
            # Ratio Spread
            if len(long_calls) == 1 and len(short_calls) >= 2 and not long_puts and not short_puts:
                return cls._create_result(StrategyType.RATIO_CALL_SPREAD, options, None, 0.8)
            
            if len(long_puts) == 1 and len(short_puts) >= 2 and not long_calls and not short_calls:
                return cls._create_result(StrategyType.RATIO_PUT_SPREAD, options, None, 0.8)
        
        # 無法識別
        return cls._create_result(StrategyType.CUSTOM, options, stock, 0.5)
    
    @classmethod
    def _create_result(
        cls,
        strategy_type: StrategyType,
        options: List[OptionLeg],
        stock: Optional[StockPosition],
        confidence: float
    ) -> StrategyResult:
        """建立策略識別結果"""
        description = cls.STRATEGY_DESCRIPTIONS.get(strategy_type, "")
        
        # 計算風險特性
        risk_profile = cls._calculate_risk_profile(strategy_type)
        max_profit, max_loss = cls._calculate_profit_loss(strategy_type, options, stock)
        breakeven = cls._calculate_breakeven(strategy_type, options, stock)
        greeks = cls._estimate_greeks(options, stock)
        
        return StrategyResult(
            strategy_type=strategy_type,
            strategy_name=strategy_type.value,
            description=description,
            risk_profile=risk_profile,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven=breakeven,
            greeks_summary=greeks,
            legs=options,
            stock=stock,
            confidence=confidence
        )
    
    @classmethod
    def _calculate_risk_profile(cls, strategy_type: StrategyType) -> str:
        """計算風險特性"""
        unlimited_risk = {
            StrategyType.SHORT_CALL, StrategyType.SHORT_STRADDLE,
            StrategyType.SHORT_STRANGLE, StrategyType.RATIO_CALL_SPREAD
        }
        
        if strategy_type in unlimited_risk:
            return "unlimited"
        return "defined"
    
    @classmethod
    def _calculate_profit_loss(
        cls,
        strategy_type: StrategyType,
        options: List[OptionLeg],
        stock: Optional[StockPosition]
    ) -> Tuple[str, str]:
        """計算最大獲利/損失"""
        # 簡化計算，實際應根據具體價格計算
        if strategy_type in {StrategyType.LONG_CALL, StrategyType.LONG_PUT}:
            return "無限", "權利金"
        elif strategy_type in {StrategyType.SHORT_CALL}:
            return "權利金", "無限"
        elif strategy_type in {StrategyType.SHORT_PUT}:
            return "權利金", "履約價 - 權利金"
        elif strategy_type in {StrategyType.COVERED_CALL}:
            return "履約價 - 成本 + 權利金", "成本 - 權利金"
        elif strategy_type in {StrategyType.IRON_CONDOR, StrategyType.IRON_BUTTERFLY}:
            return "淨權利金", "價差寬度 - 淨權利金"
        else:
            return "視情況", "視情況"
    
    @classmethod
    def _calculate_breakeven(
        cls,
        strategy_type: StrategyType,
        options: List[OptionLeg],
        stock: Optional[StockPosition]
    ) -> List[float]:
        """計算損益平衡點"""
        # 簡化計算
        return []
    
    @classmethod
    def _estimate_greeks(
        cls,
        options: List[OptionLeg],
        stock: Optional[StockPosition]
    ) -> Dict[str, float]:
        """估算 Greeks"""
        delta = 0.0
        gamma = 0.0
        theta = 0.0
        vega = 0.0
        
        # 股票 Delta
        if stock:
            delta += stock.quantity
        
        # 選擇權 Greeks（簡化估算）
        for opt in options:
            multiplier = 100
            qty = opt.quantity
            
            # Delta 估算
            if opt.is_call:
                opt_delta = 0.5 * qty * multiplier
            else:
                opt_delta = -0.5 * qty * multiplier
            
            delta += opt_delta
            gamma += 0.02 * abs(qty) * multiplier
            theta += -0.05 * qty * multiplier
            vega += 0.1 * abs(qty) * multiplier
        
        return {
            'delta': round(delta, 2),
            'gamma': round(gamma, 4),
            'theta': round(theta, 2),
            'vega': round(vega, 2)
        }
    
    @classmethod
    def detect_from_positions(
        cls,
        positions: List[Dict],
        underlying: str
    ) -> StrategyResult:
        """
        從持倉資料識別策略
        
        Args:
            positions: 持倉列表（包含股票和選擇權）
            underlying: 標的代號
            
        Returns:
            策略識別結果
        """
        options = []
        stock = None
        
        for pos in positions:
            asset_cat = pos.get('asset_category', 'STK')
            quantity = pos.get('position', 0)
            
            if asset_cat == 'STK':
                stock = StockPosition(
                    symbol=pos.get('symbol', underlying),
                    quantity=int(quantity),
                    avg_cost=pos.get('average_cost', 0),
                    current_price=pos.get('mark_price', 0)
                )
            elif asset_cat == 'OPT':
                opt_type = 'call' if pos.get('put_call') == 'C' else 'put'
                options.append(OptionLeg(
                    symbol=pos.get('symbol', ''),
                    option_type=opt_type,
                    strike=float(pos.get('strike', 0)),
                    expiry=pos.get('expiry', ''),
                    quantity=int(quantity),
                    premium=pos.get('mark_price', 0)
                ))
        
        current_price = stock.current_price if stock else 0
        return cls.detect_strategy(options, stock, current_price)


# 策略風險等級
STRATEGY_RISK_LEVELS = {
    StrategyType.STOCK_ONLY: "低",
    StrategyType.COVERED_CALL: "低",
    StrategyType.PROTECTIVE_PUT: "低",
    StrategyType.COLLAR: "低",
    StrategyType.BULL_PUT_SPREAD: "中",
    StrategyType.BEAR_CALL_SPREAD: "中",
    StrategyType.IRON_CONDOR: "中",
    StrategyType.IRON_BUTTERFLY: "中",
    StrategyType.LONG_CALL: "中",
    StrategyType.LONG_PUT: "中",
    StrategyType.BULL_CALL_SPREAD: "中",
    StrategyType.BEAR_PUT_SPREAD: "中",
    StrategyType.ZEBRA_CALL: "中",
    StrategyType.ZEBRA_PUT: "中",
    StrategyType.PMCC: "中",
    StrategyType.LONG_STRADDLE: "高",
    StrategyType.LONG_STRANGLE: "高",
    StrategyType.SHORT_PUT: "高",
    StrategyType.JADE_LIZARD: "高",
    StrategyType.SHORT_CALL: "極高",
    StrategyType.SHORT_STRADDLE: "極高",
    StrategyType.SHORT_STRANGLE: "極高",
    StrategyType.RATIO_CALL_SPREAD: "極高",
    StrategyType.RATIO_PUT_SPREAD: "極高",
}


def get_strategy_risk_level(strategy_type: StrategyType) -> str:
    """取得策略風險等級"""
    return STRATEGY_RISK_LEVELS.get(strategy_type, "中")
