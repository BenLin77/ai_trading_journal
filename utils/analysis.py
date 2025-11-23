"""
Python 規則引擎分析模組

此模組負責：
1. 偵測「追高」(Chasing Price) - 買在 K 棒最高點附近
2. 偵測「殺低」(Panic Selling) - 賣在 K 棒最低點附近
3. 分析交易時機與價格位置
"""

import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta


class TradingAnalyzer:
    """交易分析引擎"""

    def __init__(self, threshold: float = 0.02):
        """
        初始化分析器

        Args:
            threshold: 價格偏差閾值（預設 2%），用於判斷是否接近高低點
        """
        self.threshold = threshold

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """計算 RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def analyze_trades_with_bars(self,
                                  trades_df: pd.DataFrame,
                                  ohlc_df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析交易與 K 線數據，偵測交易問題
        
        Args:
            trades_df: 交易紀錄 DataFrame，需包含 datetime, action, price 欄位
            ohlc_df: K 線數據 DataFrame，需包含 datetime, high, low, close 欄位
            
        Returns:
            分析結果字典，包含各種偵測到的問題
        """
        issues = {
            'chasing_price': [],  # 追高問題
            'panic_selling': [],  # 殺低問題
            'poor_timing': [],    # 不良時機
            'summary': {}
        }

        if trades_df.empty or ohlc_df.empty:
            return issues

        # 確保日期時間格式一致
        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])
        ohlc_df['datetime'] = pd.to_datetime(ohlc_df['datetime'])

        # 預先計算指標 (RSI, MA)
        ohlc_df = ohlc_df.sort_values('datetime')
        rsi_series = self._calculate_rsi(ohlc_df['close'])
        ma5_series = ohlc_df['close'].rolling(window=5).mean()
        ma20_series = ohlc_df['close'].rolling(window=20).mean()

        # 設置 datetime 為索引以便合併
        ohlc_df_indexed = ohlc_df.set_index('datetime')
        rsi_series.index = ohlc_df['datetime']
        ma5_series.index = ohlc_df['datetime']
        ma20_series.index = ohlc_df['datetime']

        for idx, trade in trades_df.iterrows():
            trade_time = trade['datetime']
            trade_price = trade['price']
            trade_action = trade['action']

            # 找出最接近的 K 棒（允許 5 分鐘誤差）
            time_window = timedelta(minutes=5)
            mask = (ohlc_df['datetime'] >= trade_time - time_window) & \
                   (ohlc_df['datetime'] <= trade_time + time_window)
            matching_bars = ohlc_df[mask]

            if matching_bars.empty:
                continue

            # 取最接近的那根 K 棒
            closest_bar = matching_bars.iloc[(matching_bars['datetime'] - trade_time).abs().argsort()[:1]]

            if closest_bar.empty:
                continue

            bar_high = closest_bar['high'].values[0]
            bar_low = closest_bar['low'].values[0]
            bar_close = closest_bar['close'].values[0]
            bar_time = closest_bar['datetime'].values[0]

            # 計算價格範圍
            price_range = bar_high - bar_low
            if price_range == 0:
                continue

            # 取得當前指標值 (從預計算的序列中)
            current_rsi = rsi_series.loc[closest_bar.index[0]] if pd.notna(rsi_series.loc[closest_bar.index[0]]) else 50
            current_ma5 = ma5_series.loc[closest_bar.index[0]]
            current_ma20 = ma20_series.loc[closest_bar.index[0]]
            
            # 判斷趨勢狀態 (供參考，不作為絕對對錯標準)
            is_uptrend = current_ma5 > current_ma20 if pd.notna(current_ma5) and pd.notna(current_ma20) else None

            # --- 買入分析 ---
            if trade_action.upper() in ['BUY', 'BOT']:
                # 2. 追高/FOMO 偵測 (RSI > 70 且買在 K 棒高點)
                distance_to_high = abs(trade_price - bar_high)
                is_near_high = (distance_to_high / price_range < self.threshold)
                
                if current_rsi > 70:
                    issues['chasing_price'].append({
                        'trade_time': str(trade_time),
                        'message': f"疑似 FOMO 追高：在 RSI 超買區 ({current_rsi:.1f}) 買進。是動能突破策略嗎？"
                    })
                
                # 3. 接刀偵測 (下跌趨勢中，RSI 還沒到超賣區就接)
                if not is_uptrend and current_rsi > 40:
                     issues['poor_timing'].append({
                        'trade_time': str(trade_time),
                        'message': f"左側接刀風險：在下跌趨勢中買進，但 RSI ({current_rsi:.1f}) 尚未進入超賣區。確認有支撐嗎？"
                    })

            # --- 賣出分析 ---
            elif trade_action.upper() in ['SELL', 'SLD']:
                # 1. 恐慌殺盤偵測 (RSI < 30 時賣出)
                if current_rsi < 30:
                    issues['panic_selling'].append({
                        'trade_time': str(trade_time),
                        'message': f"疑似恐慌殺低：在 RSI 超賣區 ({current_rsi:.1f}) 賣出。這是紀律性停損，還是受情緒影響？"
                    })
                
                # 2. 賣在最低點 (不論 RSI)
                distance_to_low = abs(trade_price - bar_low)
                if distance_to_low / price_range < self.threshold:
                     pass # 殺低偵測已包含在 panic_selling 或作為輔助

        # 生成摘要
        issues['summary'] = {
            'total_chasing': len(issues['chasing_price']),
            'total_panic_selling': len(issues['panic_selling']),
            'total_poor_timing': len(issues['poor_timing']),
            'total_issues': len(issues['chasing_price']) + len(issues['panic_selling']) + len(issues['poor_timing'])
        }

        return issues

    def analyze_time_of_day(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """
        分析交易的時段分布

        Args:
            trades_df: 交易紀錄 DataFrame

        Returns:
            時段分析結果
        """
        if trades_df.empty:
            return {}

        trades_df['datetime'] = pd.to_datetime(trades_df['datetime'])
        trades_df['hour'] = trades_df['datetime'].dt.hour

        # 按小時分組計算盈虧
        hourly_pnl = trades_df.groupby('hour')['realized_pnl'].sum().to_dict()

        # 找出最差時段
        worst_hours = sorted(hourly_pnl.items(), key=lambda x: x[1])[:3]

        return {
            'hourly_pnl': hourly_pnl,
            'worst_hours': [
                {'hour': f"{h:02d}:00-{h+1:02d}:00", 'pnl': pnl}
                for h, pnl in worst_hours
            ]
        }

    def generate_ai_prompt_context(self, issues: Dict[str, Any]) -> str:
        """
        將分析結果轉換為 AI 提示的上下文
        
        Args:
            issues: 分析結果字典
            
        Returns:
            格式化的上下文字串，供 AI 使用
        """
        context_parts = []

        if issues['chasing_price']:
            context_parts.append(f"⚠️ 偵測到 {len(issues['chasing_price'])} 次疑似 FOMO/追高行為 (RSI過熱)：")
            for issue in issues['chasing_price'][:3]:
                context_parts.append(f"  - {issue['message']}")

        if issues['panic_selling']:
            context_parts.append(f"⚠️ 偵測到 {len(issues['panic_selling'])} 次疑似恐慌/殺低行為 (RSI過冷)：")
            for issue in issues['panic_selling'][:3]:
                context_parts.append(f"  - {issue['message']}")

        if issues['poor_timing']:
            context_parts.append(f"⚠️ 偵測到 {len(issues['poor_timing'])} 次高風險操作 (接刀/逆勢)：")
            for issue in issues['poor_timing'][:3]:
                context_parts.append(f"  - {issue['message']}")

        if not context_parts:
            context_parts.append("✅ 交易時機良好，未偵測到明顯的極端情緒操作。")

        return "\n".join(context_parts)
