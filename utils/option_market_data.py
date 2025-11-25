"""
選擇權市場數據抓取模組

功能：
1. 支援雙數據源：yfinance（免費）+ IBKR（即時）
2. 計算 Put/Call Ratio
3. 識別市場情緒指標
"""

import yfinance as yf
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import os


class OptionMarketData:
    """選擇權市場數據管理器（支援多數據源）"""

    def __init__(self, data_source: str = None):
        """
        初始化選擇權市場數據管理器

        Args:
            data_source: 數據源 ('yfinance' 或 'ibkr')，若為 None 則從環境變數讀取
        """
        self.cache = {}  # 簡易快取

        # 決定數據源
        if data_source:
            self.data_source = data_source
        else:
            self.data_source = os.getenv('OPTION_DATA_SOURCE', 'yfinance').lower()

        # 初始化 IBKR 連接（如果需要）
        self.ib = None
        if self.data_source == 'ibkr':
            self._init_ibkr_connection()

    def _init_ibkr_connection(self):
        """初始化 IBKR API 連接"""
        try:
            from ib_insync import IB

            self.ib = IB()

            # 從環境變數讀取連接參數
            host = os.getenv('IBKR_HOST', '127.0.0.1')
            port = int(os.getenv('IBKR_PORT', '7497'))  # 7497 = TWS paper, 7496 = TWS live
            client_id = int(os.getenv('IBKR_CLIENT_ID', '1'))

            self.ib.connect(host, port, clientId=client_id, readonly=True)
            print(f"✅ IBKR API 連接成功 ({host}:{port})")

        except ImportError:
            print("⚠️ 未安裝 ib_insync，請執行：uv add ib-insync")
            self.data_source = 'yfinance'  # 降級到 yfinance
        except Exception as e:
            print(f"⚠️ IBKR 連接失敗：{e}，降級使用 yfinance")
            self.data_source = 'yfinance'

    def get_option_chain(self, symbol: str, expiry_date: str = None) -> Optional[Dict[str, Any]]:
        """
        取得選擇權鏈數據（自動選擇數據源）

        Args:
            symbol: 標的代號（如 AAPL）
            expiry_date: 到期日（YYYY-MM-DD），若為 None 則取最近到期日

        Returns:
            包含 calls 和 puts 的 DataFrame
        """
        if self.data_source == 'ibkr' and self.ib:
            return self._get_option_chain_ibkr(symbol, expiry_date)
        else:
            return self._get_option_chain_yfinance(symbol, expiry_date)

    def _get_option_chain_yfinance(self, symbol: str, expiry_date: str = None) -> Optional[Dict[str, Any]]:
        """使用 yfinance 抓取選擇權鏈"""
        try:
            ticker = yf.Ticker(symbol)

            # 取得所有可用到期日
            available_dates = ticker.options

            if not available_dates:
                return None

            # 選擇到期日
            if expiry_date:
                target_date = expiry_date
            else:
                target_date = available_dates[0]  # 最近到期日

            # 抓取選擇權鏈
            chain = ticker.option_chain(target_date)

            return {
                'expiry': target_date,
                'calls': chain.calls,
                'puts': chain.puts,
                'available_dates': list(available_dates),
                'source': 'yfinance'
            }

        except Exception as e:
            print(f"Error fetching option chain for {symbol}: {e}")
            return None

    def _get_option_chain_ibkr(self, symbol: str, expiry_date: str = None) -> Optional[Dict[str, Any]]:
        """使用 IBKR API 抓取選擇權鏈"""
        try:
            from ib_insync import Stock, Option

            # 建立股票合約
            stock = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            # 取得選擇權鏈
            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)

            if not chains:
                return None

            # 選擇交易所（通常選第一個）
            chain = chains[0]

            # 取得所有到期日
            available_dates = sorted(chain.expirations)

            if not available_dates:
                return None

            # 選擇到期日
            if expiry_date:
                target_date = expiry_date.replace('-', '')  # IBKR 格式: YYYYMMDD
            else:
                target_date = available_dates[0]

            # 取得該到期日的所有履約價
            strikes = sorted(chain.strikes)

            # 批次建立選擇權合約
            call_contracts = [Option(symbol, target_date, strike, 'C', chain.exchange) for strike in strikes]
            put_contracts = [Option(symbol, target_date, strike, 'P', chain.exchange) for strike in strikes]

            # 確認合約
            self.ib.qualifyContracts(*call_contracts, *put_contracts)

            # 抓取市場數據
            call_tickers = [self.ib.reqMktData(c, '', False, False) for c in call_contracts]
            put_tickers = [self.ib.reqMktData(c, '', False, False) for c in put_contracts]

            # 等待數據
            self.ib.sleep(2)

            # 轉換為 DataFrame
            calls_data = []
            for ticker, contract in zip(call_tickers, call_contracts):
                calls_data.append({
                    'strike': contract.strike,
                    'lastPrice': ticker.last,
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'volume': ticker.volume,
                    'openInterest': ticker.openInterest if hasattr(ticker, 'openInterest') else 0,
                    'impliedVolatility': ticker.impliedVolatility if ticker.impliedVolatility else 0
                })

            puts_data = []
            for ticker, contract in zip(put_tickers, put_contracts):
                puts_data.append({
                    'strike': contract.strike,
                    'lastPrice': ticker.last,
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'volume': ticker.volume,
                    'openInterest': ticker.openInterest if hasattr(ticker, 'openInterest') else 0,
                    'impliedVolatility': ticker.impliedVolatility if ticker.impliedVolatility else 0
                })

            return {
                'expiry': datetime.strptime(target_date, '%Y%m%d').strftime('%Y-%m-%d'),
                'calls': pd.DataFrame(calls_data),
                'puts': pd.DataFrame(puts_data),
                'available_dates': [datetime.strptime(d, '%Y%m%d').strftime('%Y-%m-%d') for d in available_dates],
                'source': 'ibkr'
            }

        except Exception as e:
            print(f"Error fetching IBKR option chain for {symbol}: {e}")
            return None

    def analyze_option_position(self, symbol: str, strike: float, option_type: str, expiry: str) -> Dict[str, Any]:
        """
        分析特定選擇權部位的市場數據

        Args:
            symbol: 標的代號
            strike: 履約價
            option_type: 'Call' 或 'Put'
            expiry: 到期日（YYYY-MM-DD）

        Returns:
            包含 volume, openInterest, impliedVolatility 等資訊
        """
        chain_data = self.get_option_chain(symbol, expiry)

        if not chain_data:
            return {'error': 'Unable to fetch option chain'}

        # 選擇 calls 或 puts
        df = chain_data['calls'] if option_type == 'Call' else chain_data['puts']

        # 找到對應履約價
        matching = df[df['strike'] == strike]

        if matching.empty:
            return {'error': f'No data for strike {strike}'}

        row = matching.iloc[0]

        return {
            'strike': strike,
            'type': option_type,
            'expiry': expiry,
            'last_price': row.get('lastPrice', 0),
            'bid': row.get('bid', 0),
            'ask': row.get('ask', 0),
            'volume': row.get('volume', 0),
            'open_interest': row.get('openInterest', 0),
            'implied_volatility': row.get('impliedVolatility', 0) * 100,  # 轉為百分比
            'in_the_money': row.get('inTheMoney', False)
        }

    def get_portfolio_option_metrics(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批次分析投資組合中的選擇權部位

        Args:
            positions: 持倉列表，每個包含 symbol, strike, option_type, expiry

        Returns:
            彙總的市場指標
        """
        results = []

        for pos in positions:
            if pos.get('instrument_type') not in ['option', 'option_combo']:
                continue

            underlying = pos.get('underlying', pos.get('symbol'))

            # 處理組合策略（取第一腿作為代表）
            if pos.get('instrument_type') == 'option_combo':
                strike = pos.get('strike_low', pos.get('strike'))
            else:
                strike = pos.get('strike')

            if not strike or not pos.get('expiry'):
                continue

            analysis = self.analyze_option_position(
                underlying,
                float(strike),
                pos.get('option_type', 'Call'),
                pos.get('expiry')
            )

            if 'error' not in analysis:
                analysis['position_symbol'] = pos.get('symbol')
                analysis['position_quantity'] = pos.get('net_position', pos.get('position', 0))
                results.append(analysis)

        return {
            'total_positions': len(results),
            'details': results,
            'avg_iv': sum(r.get('implied_volatility', 0) for r in results) / len(results) if results else 0,
            'total_volume': sum(r.get('volume', 0) for r in results),
            'total_open_interest': sum(r.get('open_interest', 0) for r in results)
        }

    def calculate_put_call_ratio(self, symbol: str, expiry: str = None) -> Dict[str, float]:
        """
        計算 Put/Call Ratio（市場情緒指標）

        Args:
            symbol: 標的代號
            expiry: 到期日

        Returns:
            Volume Ratio 與 OI Ratio
        """
        chain_data = self.get_option_chain(symbol, expiry)

        if not chain_data:
            return {'error': 'Unable to fetch data'}

        calls = chain_data['calls']
        puts = chain_data['puts']

        call_volume = calls['volume'].sum()
        put_volume = puts['volume'].sum()
        call_oi = calls['openInterest'].sum()
        put_oi = puts['openInterest'].sum()

        volume_ratio = put_volume / call_volume if call_volume > 0 else 0
        oi_ratio = put_oi / call_oi if call_oi > 0 else 0

        # 情緒判斷
        sentiment = "中性"
        if volume_ratio > 1.2:
            sentiment = "看跌（Put 交易量高）"
        elif volume_ratio < 0.8:
            sentiment = "看漲（Call 交易量高）"

        return {
            'volume_ratio': volume_ratio,
            'oi_ratio': oi_ratio,
            'call_volume': call_volume,
            'put_volume': put_volume,
            'call_oi': call_oi,
            'put_oi': put_oi,
            'sentiment': sentiment
        }

    def get_iv_skew(self, symbol: str, expiry: str = None) -> Dict[str, Any]:
        """
        取得 IV Skew（波動率偏斜）

        Args:
            symbol: 標的代號
            expiry: 到期日

        Returns:
            不同履約價的 IV 分布
        """
        chain_data = self.get_option_chain(symbol, expiry)

        if not chain_data:
            return {'error': 'Unable to fetch data'}

        calls = chain_data['calls'][['strike', 'impliedVolatility']].copy()
        calls['type'] = 'Call'

        puts = chain_data['puts'][['strike', 'impliedVolatility']].copy()
        puts['type'] = 'Put'

        iv_data = pd.concat([calls, puts])
        iv_data['impliedVolatility'] = iv_data['impliedVolatility'] * 100

        return {
            'expiry': chain_data['expiry'],
            'iv_skew_data': iv_data.to_dict('records'),
            'atm_iv': iv_data.sort_values('strike').iloc[len(iv_data)//2]['impliedVolatility']
        }
