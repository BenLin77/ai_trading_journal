"""
AI 上下文建構器

此模組負責收集交易分析所需的各種數據，為 AI 提供完整的上下文：
1. 當前倉位
2. K 線圖數據（價格走勢、支撐阻力、ATR）
3. 技術指標
4. Gamma Level (未來擴展)

設計原則：可擴展，新增數據源只需加入對應的 getter 方法
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AIContextBuilder:
    """AI 上下文建構器"""

    def __init__(self, db):
        """
        初始化

        Args:
            db: TradingDatabase 實例
        """
        self.db = db

    def build_symbol_context(
        self,
        symbol: str,
        include_positions: bool = True,
        include_chart: bool = True,
        include_gamma: bool = False,  # 未來擴展
        lookback_days: int = 30
    ) -> str:
        """
        建構單一標的的完整上下文

        Args:
            symbol: 股票代號
            include_positions: 是否包含倉位數據
            include_chart: 是否包含 K 線圖數據
            include_gamma: 是否包含 Gamma Level（未來擴展）
            lookback_days: K 線回看天數

        Returns:
            Markdown 格式的上下文字串
        """
        context_parts = []

        # 1. 當前倉位
        if include_positions:
            position_context = self._get_position_context(symbol)
            if position_context:
                context_parts.append(position_context)

        # 2. K 線圖數據
        if include_chart:
            chart_context = self._get_chart_context(symbol, lookback_days)
            if chart_context:
                context_parts.append(chart_context)

        # 3. Gamma Level（預留介面）
        if include_gamma:
            gamma_context = self._get_gamma_context(symbol)
            if gamma_context:
                context_parts.append(gamma_context)

        return "\n\n".join(context_parts) if context_parts else ""

    def _get_position_context(self, symbol: str) -> Optional[str]:
        """取得當前倉位上下文"""
        try:
            positions = self.db.get_latest_positions()
            if not positions:
                return None

            # 過濾相關標的（包含選擇權）
            from utils.derivatives_support import InstrumentParser
            parser = InstrumentParser()
            
            related_positions = []
            for pos in positions:
                pos_symbol = pos.get('symbol', '')
                parsed = parser.parse_symbol(pos_symbol)
                underlying = parsed.get('underlying', pos_symbol)
                
                if underlying.upper() == symbol.upper():
                    related_positions.append(pos)

            if not related_positions:
                return None

            context = "## 📊 當前倉位\n"
            
            total_market_value = 0
            total_unrealized = 0
            
            for pos in related_positions:
                qty = pos.get('position', pos.get('quantity', 0))
                avg_cost = pos.get('avg_cost', 0)
                mark_price = pos.get('mark_price', pos.get('current_price', 0))
                market_value = mark_price * abs(qty) if mark_price else 0
                unrealized = pos.get('unrealized_pnl', 0)
                
                pos_type = "股票" if not pos.get('symbol', '').count(' ') else "選擇權"
                
                context += f"- **{pos.get('symbol')}** ({pos_type})\n"
                context += f"  - 數量: {int(qty):+d}\n"
                context += f"  - 均價: ${avg_cost:.2f}\n"
                context += f"  - 現價: ${mark_price:.2f}\n"
                context += f"  - 未實現盈虧: ${unrealized:+,.2f}\n"
                
                total_market_value += market_value
                total_unrealized += unrealized

            context += f"\n**總市值**: ${total_market_value:,.2f} | **總未實現盈虧**: ${total_unrealized:+,.2f}\n"
            
            return context

        except Exception as e:
            logger.warning(f"取得倉位上下文失敗: {e}")
            return None

    def _get_chart_context(self, symbol: str, lookback_days: int = 30) -> Optional[str]:
        """取得 K 線圖上下文（價格走勢、支撐阻力、技術指標）"""
        try:
            import yfinance as yf
            
            # 取得歷史數據
            ticker = yf.Ticker(symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)  # 多取幾天以確保足夠數據
            
            hist = ticker.history(start=start_date.strftime('%Y-%m-%d'))
            
            if len(hist) < 5:
                return None

            # 基本價格數據
            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            high_52w = float(hist['High'].max())
            low_52w = float(hist['Low'].min())
            
            # 計算技術指標
            closes = hist['Close'].values
            highs = hist['High'].values
            lows = hist['Low'].values
            
            # 20 日均線
            sma_20 = closes[-20:].mean() if len(closes) >= 20 else closes.mean()
            
            # ATR (Average True Range) - 14 日
            atr = self._calculate_atr(highs, lows, closes, period=14)
            
            # 支撐阻力（近期高低點）
            recent_high = float(hist['High'].tail(10).max())
            recent_low = float(hist['Low'].tail(10).min())
            
            # 趨勢判斷
            if current_price > sma_20:
                trend = "📈 多頭（價格在 20MA 上方）"
            else:
                trend = "📉 空頭（價格在 20MA 下方）"

            context = f"""## 📈 K 線圖分析 ({symbol})

### 價格數據
- **當前價格**: ${current_price:.2f} ({change_pct:+.2f}%)
- **20 日均線**: ${sma_20:.2f}
- **趨勢判斷**: {trend}

### 波動性指標
- **ATR (14日)**: ${atr:.2f} ({(atr/current_price)*100:.1f}%)
- **近期高點 (10日)**: ${recent_high:.2f}
- **近期低點 (10日)**: ${recent_low:.2f}
- **{lookback_days}日高點**: ${high_52w:.2f}
- **{lookback_days}日低點**: ${low_52w:.2f}

### 關鍵價位建議
- **阻力位**: ${recent_high:.2f} (近期高點)
- **支撐位**: ${recent_low:.2f} (近期低點)
- **動態停損建議 (1.5 ATR)**: ${current_price - 1.5 * atr:.2f}
"""
            return context

        except Exception as e:
            logger.warning(f"取得 K 線圖上下文失敗: {e}")
            return None

    def _calculate_atr(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 14
    ) -> float:
        """計算 ATR (Average True Range)"""
        if len(closes) < period + 1:
            return 0.0
        
        tr_list = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        if len(tr_list) >= period:
            return sum(tr_list[-period:]) / period
        return sum(tr_list) / len(tr_list) if tr_list else 0.0

    def _get_gamma_context(self, symbol: str) -> Optional[str]:
        """
        取得 Gamma Level 上下文
        
        TODO: 未來實作
        - 整合 Gamma Level API
        - 識別關鍵 Gamma 翻轉點
        - 計算 Put/Call 牆位置
        """
        # 預留介面，未來擴展
        return None

    def get_portfolio_summary(self) -> str:
        """取得整體投資組合摘要"""
        try:
            positions = self.db.get_latest_positions()
            stats = self.db.get_trade_statistics()
            
            if not positions:
                return "目前沒有持倉。"

            context = "## 📊 投資組合摘要\n\n"
            
            # 統計數據
            total_value = sum(
                (p.get('mark_price', 0) or 0) * abs(p.get('position', 0) or p.get('quantity', 0))
                for p in positions
            )
            total_unrealized = sum(p.get('unrealized_pnl', 0) or 0 for p in positions)
            
            context += f"- **持倉數量**: {len(positions)} 個標的\n"
            context += f"- **總市值**: ${total_value:,.2f}\n"
            context += f"- **總未實現盈虧**: ${total_unrealized:+,.2f}\n"
            
            if stats:
                context += f"- **歷史勝率**: {stats.get('win_rate', 0):.1f}%\n"
                context += f"- **獲利因子**: {stats.get('profit_factor', 0):.2f}\n"

            # 主要持倉
            context += "\n### 主要持倉\n"
            sorted_positions = sorted(
                positions,
                key=lambda x: abs((x.get('mark_price', 0) or 0) * (x.get('position', 0) or x.get('quantity', 0))),
                reverse=True
            )
            
            for pos in sorted_positions[:5]:
                symbol = pos.get('symbol', 'N/A')
                qty = pos.get('position', pos.get('quantity', 0))
                unrealized = pos.get('unrealized_pnl', 0) or 0
                context += f"- {symbol}: {int(qty):+d} 股, 未實現盈虧 ${unrealized:+,.2f}\n"

            return context

        except Exception as e:
            logger.warning(f"取得投資組合摘要失敗: {e}")
            return "無法取得投資組合數據。"
