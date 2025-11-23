"""
選擇權與期貨支援模組

此模組負責：
1. 識別交易標的類型（股票/選擇權/期貨）
2. 解析選擇權代號（Strike、到期日、Call/Put）
3. 選擇權策略分析（Spread、Straddle、Iron Condor 等）
4. Greeks 計算與視覺化
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd


class InstrumentParser:
    """標的類型識別與解析器"""

    @staticmethod
    def parse_symbol(symbol: str) -> Dict[str, Any]:
        """
        解析標的代號，識別類型並提取資訊

        Args:
            symbol: 標的代號

        Returns:
            標的資訊字典
        """
        result = {
            'original_symbol': symbol,
            'instrument_type': 'stock',
            'underlying': symbol,
            'strike': None,
            'expiry': None,
            'option_type': None,
            'multiplier': 1
        }

        # 選擇權格式 1: OCC 格式 (AAPL240119C00150000)
        # 格式: [Underlying][YYMMDD][C/P][8位價格]
        occ_pattern = r'^([A-Z]+)(\d{6})([CP])(\d{8})$'
        match = re.match(occ_pattern, symbol)

        if match:
            underlying, date_str, option_type, strike_str = match.groups()

            result.update({
                'instrument_type': 'option',
                'underlying': underlying,
                'expiry': datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d'),
                'option_type': 'Call' if option_type == 'C' else 'Put',
                'strike': float(strike_str) / 1000,  # Strike 以千為單位
                'multiplier': 100  # 美股選擇權標準倍數
            })
            return result

        # 選擇權格式 2: 人類可讀格式 (AAPL 2024-01-19 150 Call)
        readable_pattern = r'^([A-Z]+)\s+(\d{4}-\d{2}-\d{2})\s+([\d.]+)\s+(Call|Put)$'
        match = re.match(readable_pattern, symbol, re.IGNORECASE)

        if match:
            underlying, expiry, strike, option_type = match.groups()

            result.update({
                'instrument_type': 'option',
                'underlying': underlying,
                'expiry': expiry,
                'option_type': option_type.capitalize(),
                'strike': float(strike),
                'multiplier': 100
            })
            return result

        # 期貨格式: ESZ24 (ES = 標普500, Z = 12月, 24 = 2024)
        # 常見期貨代號: ES, NQ, YM, CL, GC, SI
        futures_pattern = r'^([A-Z]{1,3})([FGHJKMNQUVXZ])(\d{2})$'
        match = re.match(futures_pattern, symbol)

        if match:
            underlying, month_code, year = match.groups()

            # 月份代碼對應
            month_codes = {
                'F': '01', 'G': '02', 'H': '03', 'J': '04',
                'K': '05', 'M': '06', 'N': '07', 'Q': '08',
                'U': '09', 'V': '10', 'X': '11', 'Z': '12'
            }

            expiry_date = f"20{year}-{month_codes[month_code]}-15"  # 假設15日到期

            result.update({
                'instrument_type': 'futures',
                'underlying': underlying,
                'expiry': expiry_date,
                'multiplier': 50  # 預設倍數，實際需根據合約調整
            })
            return result

        # 如果都不匹配，判定為股票
        return result

    @staticmethod
    def is_option(symbol: str) -> bool:
        """判斷是否為選擇權"""
        parsed = InstrumentParser.parse_symbol(symbol)
        return parsed['instrument_type'] == 'option'

    @staticmethod
    def is_futures(symbol: str) -> bool:
        """判斷是否為期貨"""
        parsed = InstrumentParser.parse_symbol(symbol)
        return parsed['instrument_type'] == 'futures'


class OptionsStrategyAnalyzer:
    """選擇權策略分析器"""

    @staticmethod
    def identify_strategy(trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        識別選擇權交易策略

        Args:
            trades_df: 交易紀錄 DataFrame

        Returns:
            策略分析結果
        """
        if trades_df.empty:
            return {'strategy': 'unknown', 'legs': []}

        # 按時間分組（同一時間的交易視為組合策略）
        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])
        grouped = trades_df.groupby(trades_df['datetime'].dt.date)

        strategies = []

        for date, group in grouped:
            # 解析每個交易
            legs = []
            for _, trade in group.iterrows():
                parsed = InstrumentParser.parse_symbol(trade['symbol'])
                if parsed['instrument_type'] == 'option':
                    legs.append({
                        'underlying': parsed['underlying'],
                        'strike': parsed['strike'],
                        'expiry': parsed['expiry'],
                        'option_type': parsed['option_type'],
                        'action': trade['action'],
                        'quantity': trade['quantity']
                    })

            if legs:
                strategy_name = OptionsStrategyAnalyzer._classify_strategy(legs)
                strategies.append({
                    'date': str(date),
                    'strategy': strategy_name,
                    'legs': legs
                })

        return {
            'total_strategies': len(strategies),
            'strategies': strategies
        }

    @staticmethod
    def _classify_strategy(legs: List[Dict]) -> str:
        """根據腳位分類策略"""
        if len(legs) == 1:
            return "Long Call" if legs[0]['option_type'] == 'Call' else "Long Put"

        if len(legs) == 2:
            # 檢查是否為 Spread
            if legs[0]['option_type'] == legs[1]['option_type']:
                if legs[0]['strike'] != legs[1]['strike']:
                    return f"{legs[0]['option_type']} Spread"

            # 檢查是否為 Straddle/Strangle
            if legs[0]['strike'] == legs[1]['strike']:
                return "Straddle"
            else:
                return "Strangle"

        if len(legs) == 4:
            # 可能是 Iron Condor 或 Iron Butterfly
            strikes = sorted([leg['strike'] for leg in legs])
            if strikes[0] < strikes[1] < strikes[2] < strikes[3]:
                return "Iron Condor"

        return f"Complex Strategy ({len(legs)} legs)"


class DerivativesAnalyzer:
    """衍生性商品綜合分析器"""

    def __init__(self):
        self.parser = InstrumentParser()
        self.strategy_analyzer = OptionsStrategyAnalyzer()

    def enrich_trades(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """
        豐富交易數據，加入衍生品資訊

        Args:
            trades_df: 原始交易數據

        Returns:
            豐富後的 DataFrame
        """
        enriched = trades_df.copy()

        # 解析每個標的
        parsed_info = trades_df['symbol'].apply(self.parser.parse_symbol)

        # 展開解析結果
        enriched['instrument_type'] = parsed_info.apply(lambda x: x['instrument_type'])
        enriched['underlying'] = parsed_info.apply(lambda x: x['underlying'])
        enriched['strike'] = parsed_info.apply(lambda x: x['strike'])
        enriched['expiry'] = parsed_info.apply(lambda x: x['expiry'])
        enriched['option_type'] = parsed_info.apply(lambda x: x['option_type'])
        enriched['multiplier'] = parsed_info.apply(lambda x: x['multiplier'])

        # 計算名義價值
        enriched['notional_value'] = enriched['quantity'] * enriched['price'] * enriched['multiplier']

        return enriched

    def calculate_options_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        計算選擇權專屬指標

        Args:
            trades_df: 交易數據

        Returns:
            選擇權指標
        """
        enriched = self.enrich_trades(trades_df)
        options_only = enriched[enriched['instrument_type'] == 'option']

        if options_only.empty:
            return {'has_options': False}

        metrics = {
            'has_options': True,
            'total_options_trades': len(options_only),
            'call_trades': len(options_only[options_only['option_type'] == 'Call']),
            'put_trades': len(options_only[options_only['option_type'] == 'Put']),
            'total_premium': options_only['notional_value'].sum(),
            'avg_premium_per_trade': options_only['notional_value'].mean(),
            'strategies': self.strategy_analyzer.identify_strategy(options_only)
        }

        return metrics

    def calculate_futures_metrics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        計算期貨專屬指標

        Args:
            trades_df: 交易數據

        Returns:
            期貨指標
        """
        enriched = self.enrich_trades(trades_df)
        futures_only = enriched[enriched['instrument_type'] == 'futures']

        if futures_only.empty:
            return {'has_futures': False}

        metrics = {
            'has_futures': True,
            'total_futures_trades': len(futures_only),
            'total_contracts': futures_only['quantity'].sum(),
            'total_notional': futures_only['notional_value'].sum(),
            'avg_holding_period': None  # 需要配對買賣才能計算
        }

        return metrics

    def generate_derivatives_report(self, trades_df: pd.DataFrame) -> str:
        """
        生成衍生品交易報告

        Args:
            trades_df: 交易數據

        Returns:
            Markdown 格式報告
        """
        enriched = self.enrich_trades(trades_df)

        report = ["# 📊 衍生性商品交易分析報告\n"]

        # 統計摘要
        instrument_counts = enriched['instrument_type'].value_counts()
        report.append("## 交易標的分布\n")
        for inst_type, count in instrument_counts.items():
            report.append(f"- **{inst_type.upper()}**: {count} 筆")

        # 選擇權分析
        options_metrics = self.calculate_options_metrics(trades_df)
        if options_metrics.get('has_options'):
            report.append("\n## 選擇權交易分析\n")
            report.append(f"- 總交易筆數: {options_metrics['total_options_trades']}")
            report.append(f"- Call 交易: {options_metrics['call_trades']}")
            report.append(f"- Put 交易: {options_metrics['put_trades']}")
            report.append(f"- 總權利金: ${options_metrics['total_premium']:,.2f}")

            strategies = options_metrics['strategies']
            if strategies['total_strategies'] > 0:
                report.append(f"\n### 識別的策略組合: {strategies['total_strategies']} 個\n")
                for strat in strategies['strategies'][:5]:  # 只顯示前5個
                    report.append(f"- **{strat['date']}**: {strat['strategy']}")

        # 期貨分析
        futures_metrics = self.calculate_futures_metrics(trades_df)
        if futures_metrics.get('has_futures'):
            report.append("\n## 期貨交易分析\n")
            report.append(f"- 總交易筆數: {futures_metrics['total_futures_trades']}")
            report.append(f"- 總合約數: {futures_metrics['total_contracts']}")
            report.append(f"- 名義價值: ${futures_metrics['total_notional']:,.2f}")

        return "\n".join(report)
