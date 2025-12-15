"""
MFE/MAE 計算器

此模組負責：
1. 計算每筆交易的 MFE (Max Favorable Excursion) - 最大浮盈
2. 計算每筆交易的 MAE (Max Adverse Excursion) - 最大浮虧
3. 計算交易效率 (Trade Efficiency)
4. 識別交易執行品質問題

MFE/MAE 是評估交易執行品質的黃金指標：
- MFE 高但實現盈虧低 = 出場太早或太晚
- MAE 高但最終虧損 = 停損不夠果斷
- Trade Efficiency = Realized P&L / MFE = 抓住多少潛在利潤
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MFEMAECalculator:
    """MFE/MAE 計算器"""

    def __init__(self, db):
        """
        初始化計算器

        Args:
            db: TradingDatabase 實例
        """
        self.db = db

    def calculate_for_trade(
        self,
        trade_id: str,
        symbol: str,
        entry_date: str,
        entry_price: float,
        exit_date: Optional[str] = None,
        exit_price: Optional[float] = None,
        direction: str = 'long'
    ) -> Dict[str, Any]:
        """
        計算單筆交易的 MFE/MAE

        Args:
            trade_id: 交易 ID
            symbol: 標的代號
            entry_date: 進場日期 (YYYY-MM-DD)
            entry_price: 進場價格
            exit_date: 出場日期 (可選，未平倉則用今天)
            exit_price: 出場價格 (可選)
            direction: 交易方向 ('long' or 'short')

        Returns:
            包含 MFE, MAE, trade_efficiency 等的字典
        """
        # 標準化日期格式
        entry_date = self._normalize_date(entry_date)
        if exit_date:
            exit_date = self._normalize_date(exit_date)
        else:
            exit_date = datetime.now().strftime('%Y-%m-%d')

        # 從緩存取得 OHLC 數據
        ohlc_data = self.db.get_ohlc_cache(symbol, start_date=entry_date, end_date=exit_date)

        if not ohlc_data:
            logger.warning(f"No OHLC data found for {symbol} from {entry_date} to {exit_date}")
            return self._empty_result(trade_id, symbol, entry_date, entry_price)

        # 計算 MFE 和 MAE
        mfe, mfe_price, mfe_date = self._calculate_mfe(ohlc_data, entry_price, direction)
        mae, mae_price, mae_date = self._calculate_mae(ohlc_data, entry_price, direction)

        # 計算持倉天數
        try:
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            exit_dt = datetime.strptime(exit_date, '%Y-%m-%d')
            holding_days = (exit_dt - entry_dt).days
        except Exception:
            holding_days = len(ohlc_data)

        # 計算實際盈虧和交易效率
        realized_pnl = None
        trade_efficiency = None
        max_drawdown_from_peak = None

        if exit_price is not None:
            if direction == 'long':
                realized_pnl = ((exit_price - entry_price) / entry_price) * 100
            else:
                realized_pnl = ((entry_price - exit_price) / entry_price) * 100

            # 交易效率 = 實現盈虧 / MFE (如果 MFE > 0)
            if mfe and mfe > 0:
                trade_efficiency = realized_pnl / mfe
            elif mfe == 0:
                trade_efficiency = 0 if realized_pnl <= 0 else 1

            # 計算從最高點的回撤
            if mfe and mfe > 0:
                max_drawdown_from_peak = mfe - realized_pnl

        result = {
            'trade_id': trade_id,
            'symbol': symbol,
            'entry_date': entry_date,
            'exit_date': exit_date if exit_price else None,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'mfe': round(mfe, 2) if mfe is not None else None,
            'mae': round(mae, 2) if mae is not None else None,
            'mfe_price': round(mfe_price, 2) if mfe_price else None,
            'mae_price': round(mae_price, 2) if mae_price else None,
            'mfe_date': mfe_date,
            'mae_date': mae_date,
            'realized_pnl': round(realized_pnl, 2) if realized_pnl is not None else None,
            'trade_efficiency': round(trade_efficiency, 3) if trade_efficiency is not None else None,
            'holding_days': holding_days,
            'max_drawdown_from_peak': round(max_drawdown_from_peak, 2) if max_drawdown_from_peak is not None else None,
            'direction': direction
        }

        return result

    def _calculate_mfe(
        self,
        ohlc_data: List[Dict],
        entry_price: float,
        direction: str
    ) -> Tuple[float, float, str]:
        """
        計算 MFE (最大浮盈)

        Returns:
            (mfe_percentage, mfe_price, mfe_date)
        """
        if not ohlc_data:
            return 0, entry_price, None

        if direction == 'long':
            # 做多：找最高價
            best = max(ohlc_data, key=lambda x: x['high'])
            mfe_price = best['high']
            mfe = ((mfe_price - entry_price) / entry_price) * 100
        else:
            # 做空：找最低價
            best = min(ohlc_data, key=lambda x: x['low'])
            mfe_price = best['low']
            mfe = ((entry_price - mfe_price) / entry_price) * 100

        return max(0, mfe), mfe_price, best['date']

    def _calculate_mae(
        self,
        ohlc_data: List[Dict],
        entry_price: float,
        direction: str
    ) -> Tuple[float, float, str]:
        """
        計算 MAE (最大浮虧)

        Returns:
            (mae_percentage, mae_price, mae_date) - MAE 為負數
        """
        if not ohlc_data:
            return 0, entry_price, None

        if direction == 'long':
            # 做多：找最低價
            worst = min(ohlc_data, key=lambda x: x['low'])
            mae_price = worst['low']
            mae = ((mae_price - entry_price) / entry_price) * 100
        else:
            # 做空：找最高價
            worst = max(ohlc_data, key=lambda x: x['high'])
            mae_price = worst['high']
            mae = ((entry_price - mae_price) / entry_price) * 100

        return min(0, mae), mae_price, worst['date']

    def _normalize_date(self, date_str: str) -> str:
        """標準化日期格式為 YYYY-MM-DD"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')

        # 處理 YYYYMMDD 格式
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # 處理 ISO 格式
        if 'T' in date_str:
            return date_str.split('T')[0]

        # 如果已經是 YYYY-MM-DD 格式
        if len(date_str) >= 10 and date_str[4] == '-':
            return date_str[:10]

        return date_str

    def _empty_result(
        self,
        trade_id: str,
        symbol: str,
        entry_date: str,
        entry_price: float
    ) -> Dict[str, Any]:
        """返回空的結果結構"""
        return {
            'trade_id': trade_id,
            'symbol': symbol,
            'entry_date': entry_date,
            'exit_date': None,
            'entry_price': entry_price,
            'exit_price': None,
            'mfe': None,
            'mae': None,
            'mfe_price': None,
            'mae_price': None,
            'mfe_date': None,
            'mae_date': None,
            'realized_pnl': None,
            'trade_efficiency': None,
            'holding_days': 0,
            'max_drawdown_from_peak': None
        }

    def calculate_all_trades(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        計算所有交易的 MFE/MAE
        
        設計原則：
        1. 每個「買入→賣出」配對是一筆記錄
        2. 如果股票持有期間有選擇權交易，會標記為 combo
        3. 純選擇權交易單獨處理

        Args:
            symbol: 可選，只計算特定標的

        Returns:
            MFE/MAE 結果列表
        """
        from utils.derivatives_support import InstrumentParser
        
        parser = InstrumentParser()
        trades = self.db.get_trades()
        
        if symbol:
            trades = [t for t in trades if t['symbol'] == symbol or
                     parser.parse_symbol(t['symbol']).get('underlying') == symbol]

        results = []
        positions = {}  # symbol -> list of buys

        for trade in sorted(trades, key=lambda x: x['datetime']):
            sym = trade['symbol']
            parsed = parser.parse_symbol(sym)
            underlying = parsed.get('underlying', sym)
            instrument_type = parsed.get('instrument_type', 'stock')
            action = trade['action'].upper()
            qty = abs(trade['quantity'])
            price = trade['price']
            date_str = trade['datetime']

            # 標準化日期
            if len(date_str) == 8:
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            elif 'T' in date_str:
                date_str = date_str.split('T')[0]

            if action in ['BUY', 'BOT']:
                if sym not in positions:
                    positions[sym] = []
                positions[sym].append({
                    'trade_id': trade.get('trade_id'),
                    'entry_date': date_str,
                    'entry_price': price,
                    'quantity': qty,
                    'underlying': underlying,
                    'instrument_type': instrument_type
                })
            elif action in ['SELL', 'SLD'] and sym in positions and positions[sym]:
                entry = positions[sym].pop(0)
                
                # 計算盈虧
                if entry['entry_price'] > 0:
                    realized_pnl = ((price - entry['entry_price']) / entry['entry_price']) * 100
                else:
                    realized_pnl = 0

                # 判斷策略類型
                strategy_type = instrument_type
                
                # 如果是股票，檢查同時期是否有選擇權
                if instrument_type == 'stock':
                    # 檢查是否有相同 underlying 的選擇權持倉
                    has_options = any(
                        k != sym and 
                        parser.parse_symbol(k).get('underlying') == underlying and
                        positions.get(k, [])
                        for k in positions.keys()
                    )
                    if has_options:
                        strategy_type = 'combo'
                
                # 計算 MFE/MAE（僅對股票和組合策略）
                mfe, mae = None, None
                mfe_price, mae_price = None, None
                mfe_date, mae_date = None, None
                
                if instrument_type == 'stock' or strategy_type == 'combo':
                    result = self.calculate_for_trade(
                        trade_id=entry['trade_id'],
                        symbol=underlying,
                        entry_date=entry['entry_date'],
                        entry_price=entry['entry_price'],
                        exit_date=date_str,
                        exit_price=price,
                        direction='long'
                    )
                    mfe = result.get('mfe')
                    mae = result.get('mae')
                    mfe_price = result.get('mfe_price')
                    mae_price = result.get('mae_price')
                    mfe_date = result.get('mfe_date')
                    mae_date = result.get('mae_date')
                else:
                    # 選擇權：用 realized_pnl 作為 MFE/MAE
                    mfe = max(0, realized_pnl)
                    mae = min(0, realized_pnl)

                # 計算交易效率
                trade_efficiency = None
                if mfe and mfe > 0:
                    trade_efficiency = realized_pnl / mfe
                elif mfe == 0:
                    trade_efficiency = 1.0 if realized_pnl >= 0 else 0.0
                
                # 計算持倉天數
                try:
                    entry_dt = datetime.strptime(entry['entry_date'], '%Y-%m-%d')
                    exit_dt = datetime.strptime(date_str, '%Y-%m-%d')
                    holding_days = (exit_dt - entry_dt).days
                except Exception:
                    holding_days = 0

                result = {
                    'trade_id': entry['trade_id'],
                    'symbol': underlying,
                    'original_symbol': sym,
                    'instrument_type': strategy_type,
                    'entry_date': entry['entry_date'],
                    'exit_date': date_str,
                    'entry_price': round(entry['entry_price'], 2),
                    'exit_price': round(price, 2),
                    'mfe': round(mfe, 2) if mfe is not None else None,
                    'mae': round(mae, 2) if mae is not None else None,
                    'mfe_price': mfe_price,
                    'mae_price': mae_price,
                    'mfe_date': mfe_date,
                    'mae_date': mae_date,
                    'realized_pnl': round(realized_pnl, 2),
                    'trade_efficiency': round(trade_efficiency, 3) if trade_efficiency is not None else None,
                    'holding_days': holding_days,
                    'max_drawdown_from_peak': None,
                    'direction': 'long'
                }

                if result.get('mfe') is not None or result.get('realized_pnl') is not None:
                    self.db.upsert_mfe_mae(result)
                    results.append(result)

        return results

    def get_efficiency_analysis(self) -> Dict[str, Any]:
        """
        獲取交易效率分析報告

        Returns:
            包含各種效率指標的分析報告（區分股票和選擇權）
        """
        from utils.derivatives_support import InstrumentParser
        parser = InstrumentParser()
        
        stats = self.db.get_mfe_mae_stats()
        records = self.db.get_mfe_mae_by_symbol()

        if not records:
            return {
                'total_trades': 0,
                'message': '沒有足夠的 MFE/MAE 數據進行分析',
                'stock': {'records': [], 'stats': {}},
                'derivatives': {'records': [], 'stats': {}},
            }

        # 分類規則：
        # - stock: 純股票
        # - combo: 股票+選擇權組合（如 Covered Call）→ 歸類到股票
        # - option: 純選擇權 → 歸類到衍生性商品
        # - futures: 純期貨 → 歸類到衍生性商品
        stock_records = []  # 包含 stock 和 combo
        derivatives_records = []  # 純選擇權和純期貨
        
        for r in records:
            instrument_type = r.get('instrument_type', 'stock')
            
            # combo（股票+選擇權組合）視為股票策略
            if instrument_type in ('stock', 'combo'):
                stock_records.append(r)
            # 純選擇權和純期貨歸類為衍生性商品
            elif instrument_type in ('option', 'futures'):
                derivatives_records.append(r)
            else:
                stock_records.append(r)  # 預設歸到股票

        def calc_category_stats(category_records: List[Dict]) -> Dict[str, Any]:
            """計算單個分類的統計數據"""
            if not category_records:
                return {
                    'total_trades': 0,
                    'avg_mfe': 0,
                    'avg_mae': 0,
                    'avg_efficiency': 0,
                    'avg_holding_days': 0,
                    'efficient_count': 0,
                    'inefficient_count': 0,
                    'efficiency_rate': 0,
                }
            
            mfes = [r.get('mfe', 0) for r in category_records if r.get('mfe') is not None]
            maes = [r.get('mae', 0) for r in category_records if r.get('mae') is not None]
            efficiencies = [r.get('trade_efficiency', 0) for r in category_records if r.get('trade_efficiency') is not None]
            holding_days = [r.get('holding_days', 0) for r in category_records if r.get('holding_days') is not None]
            
            efficient_trades = [r for r in category_records if r.get('trade_efficiency', 0) > 0.5]
            inefficient_trades = [r for r in category_records if r.get('trade_efficiency', 0) <= 0.5 and r.get('trade_efficiency') is not None]
            
            return {
                'total_trades': len(category_records),
                'avg_mfe': sum(mfes) / len(mfes) if mfes else 0,
                'avg_mae': sum(maes) / len(maes) if maes else 0,
                'avg_efficiency': sum(efficiencies) / len(efficiencies) if efficiencies else 0,
                'avg_holding_days': sum(holding_days) / len(holding_days) if holding_days else 0,
                'efficient_count': len(efficient_trades),
                'inefficient_count': len(inefficient_trades),
                'efficiency_rate': len(efficient_trades) / len(category_records) * 100 if category_records else 0,
            }

        stock_stats = calc_category_stats(stock_records)
        derivatives_stats = calc_category_stats(derivatives_records)

        # 分類交易（整體）
        efficient_trades = [r for r in records if r.get('trade_efficiency', 0) > 0.5]
        inefficient_trades = [r for r in records if r.get('trade_efficiency', 0) <= 0.5 and r.get('trade_efficiency') is not None]
        large_mae_trades = [r for r in records if (r.get('mae') or 0) < -5]  # MAE > 5%
        missed_mfe_trades = [r for r in records if (r.get('max_drawdown_from_peak') or 0) > 10]  # 從峰值回撤 > 10%

        analysis = {
            'total_trades': len(records),
            'avg_mfe': stats.get('avg_mfe', 0),
            'avg_mae': stats.get('avg_mae', 0),
            'avg_efficiency': stats.get('avg_efficiency', 0),
            'avg_holding_days': stats.get('avg_holding_days', 0),

            'efficient_count': len(efficient_trades),
            'inefficient_count': len(inefficient_trades),
            'efficiency_rate': len(efficient_trades) / len(records) * 100 if records else 0,

            'large_mae_count': len(large_mae_trades),
            'missed_mfe_count': len(missed_mfe_trades),

            # 分類數據
            'stock': {
                'records': stock_records,
                'stats': stock_stats,
            },
            'derivatives': {
                'records': derivatives_records,
                'stats': derivatives_stats,
            },

            'issues': [],
            'suggestions': []
        }

        # 識別問題
        if analysis['avg_efficiency'] and analysis['avg_efficiency'] < 0.4:
            analysis['issues'].append('交易效率偏低：平均只抓住了 {:.0f}% 的潛在利潤'.format(analysis['avg_efficiency'] * 100))
            analysis['suggestions'].append('考慮使用移動停利或分批出場策略')

        if len(large_mae_trades) > len(records) * 0.3:
            analysis['issues'].append('停損不夠果斷：超過 30% 的交易曾經浮虧超過 5%')
            analysis['suggestions'].append('檢視停損策略，考慮更嚴格的初始停損')

        if len(missed_mfe_trades) > len(records) * 0.3:
            analysis['issues'].append('獲利回吐嚴重：超過 30% 的交易從高點大幅回撤')
            analysis['suggestions'].append('考慮在達到目標時分批獲利了結')

        if analysis['avg_holding_days'] and analysis['avg_holding_days'] < 3:
            analysis['issues'].append('持倉時間過短：可能錯過更大的趨勢')
        elif analysis['avg_holding_days'] and analysis['avg_holding_days'] > 30:
            analysis['issues'].append('持倉時間過長：資金使用效率可能偏低')

        # 衍生性商品特定問題
        if derivatives_stats['total_trades'] > 0 and derivatives_stats['avg_mae'] < -15:
            analysis['issues'].append('衍生性商品 MAE 過高 ({:.1f}%)：槓桿商品波動大，需更嚴格風控'.format(derivatives_stats['avg_mae']))
            analysis['suggestions'].append('衍生性商品建議使用更寬的初始停損，但更嚴格的時間停損')

        return analysis

    def generate_ai_context(self, symbol: Optional[str] = None) -> str:
        """
        生成 AI 分析用的 MFE/MAE 上下文

        Args:
            symbol: 可選，只生成特定標的

        Returns:
            Markdown 格式的上下文字串
        """
        analysis = self.get_efficiency_analysis()
        records = self.db.get_mfe_mae_by_symbol(symbol)

        if not records:
            return "目前沒有 MFE/MAE 分析數據。"

        context = f"""## MFE/MAE 交易效率分析

### 整體統計
- 已分析交易數: {analysis['total_trades']}
- 平均 MFE (最大浮盈): {analysis['avg_mfe']:.1f}%
- 平均 MAE (最大浮虧): {analysis['avg_mae']:.1f}%
- 平均交易效率: {analysis['avg_efficiency']*100:.0f}% (抓住的利潤比例)
- 平均持倉天數: {analysis['avg_holding_days']:.1f} 天

### 效率分布
- 高效率交易 (>50%): {analysis['efficient_count']} 筆 ({analysis['efficiency_rate']:.0f}%)
- 低效率交易 (≤50%): {analysis['inefficient_count']} 筆
- 大幅浮虧交易 (MAE>5%): {analysis['large_mae_count']} 筆
- 獲利大幅回吐: {analysis['missed_mfe_count']} 筆

### 識別的問題
"""
        for issue in analysis.get('issues', []):
            context += f"- ⚠️ {issue}\n"

        if not analysis.get('issues'):
            context += "- ✅ 目前沒有發現明顯問題\n"

        context += "\n### 改進建議\n"
        for suggestion in analysis.get('suggestions', []):
            context += f"- 💡 {suggestion}\n"

        # 添加最近幾筆交易的詳細數據
        context += "\n### 最近交易 MFE/MAE 詳情\n"
        context += "| 標的 | 進場日 | MFE | MAE | 效率 | 持倉天數 |\n"
        context += "|------|--------|-----|-----|------|----------|\n"

        for r in records[:10]:
            eff = f"{r.get('trade_efficiency', 0)*100:.0f}%" if r.get('trade_efficiency') else "N/A"
            context += f"| {r['symbol']} | {r['entry_date']} | {r.get('mfe', 0):.1f}% | {r.get('mae', 0):.1f}% | {eff} | {r.get('holding_days', 0)} |\n"

        return context
