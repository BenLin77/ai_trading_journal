"""
IBKR Flex Query 整合模組

透過 IBKR Flex Web Service API 自動取得交易記錄和庫存快照
文件：https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm
"""

import os
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class IBKRFlexQuery:
    """IBKR Flex Query API 客戶端"""

    BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet"

    def __init__(self):
        """初始化 Flex Query 客戶端"""
        self.token = os.getenv('IBKR_FLEX_TOKEN')
        self.trades_query_id = os.getenv('IBKR_TRADES_QUERY_ID')
        self.positions_query_id = os.getenv('IBKR_POSITIONS_QUERY_ID')

        if not self.token:
            raise ValueError("IBKR_FLEX_TOKEN 未設定，請在 .env 檔案中配置")

        self.session = requests.Session()

    def _request_report(self, query_id: str) -> str:
        """
        Step 1: 請求生成報表

        Args:
            query_id: Flex Query ID

        Returns:
            reference_code: 用於取得報表的參考碼
        """
        url = f"{self.BASE_URL}/FlexStatementService.SendRequest"
        params = {
            't': self.token,
            'q': query_id,
            'v': '3'  # API version 3
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 解析 XML 回應
            root = ET.fromstring(response.content)

            status = root.find('.//Status').text
            if status != 'Success':
                error_code = root.find('.//ErrorCode').text
                error_msg = root.find('.//ErrorMessage').text
                raise Exception(f"Flex Query 請求失敗: {error_code} - {error_msg}")

            reference_code = root.find('.//ReferenceCode').text
            return reference_code

        except requests.exceptions.RequestException as e:
            raise Exception(f"網路請求失敗: {str(e)}")
        except ET.ParseError as e:
            raise Exception(f"XML 解析失敗: {str(e)}")

    def _get_report(self, reference_code: str) -> str:
        """
        Step 2: 取得已生成的報表

        Args:
            reference_code: 報表參考碼

        Returns:
            content: 報表內容（XML 或 CSV）
        """
        url = f"{self.BASE_URL}/FlexStatementService.GetStatement"
        params = {
            't': self.token,
            'q': reference_code,
            'v': '3'
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 檢查是否為錯誤回應
            if '<Status>Fail</Status>' in response.text:
                root = ET.fromstring(response.content)
                error_code = root.find('.//ErrorCode').text
                error_msg = root.find('.//ErrorMessage').text
                raise Exception(f"取得報表失敗: {error_code} - {error_msg}")

            return response.text

        except requests.exceptions.RequestException as e:
            raise Exception(f"網路請求失敗: {str(e)}")

    def _detect_format(self, content: str) -> str:
        """
        偵測報表格式 (XML 或 CSV)
        
        Returns:
            'xml' 或 'csv'
        """
        content_stripped = content.strip()
        if content_stripped.startswith('<?xml') or content_stripped.startswith('<'):
            return 'xml'
        return 'csv'

    def _parse_trades_csv(self, csv_content: str) -> List[Dict]:
        """
        解析交易記錄 CSV
        
        Args:
            csv_content: Flex Query 回傳的 CSV
            
        Returns:
            trades: 交易記錄列表
        """
        from io import StringIO
        
        try:
            df = pd.read_csv(StringIO(csv_content))
        except Exception as e:
            raise Exception(f"CSV 解析失敗: {str(e)}")
        
        trades = []
        for _, row in df.iterrows():
            # 處理日期時間
            date_time = None
            if 'Date/Time' in row:
                date_time = str(row['Date/Time'])
            elif 'TradeDate' in row:
                trade_date = str(row['TradeDate'])
                trade_time = str(row.get('TradeTime', ''))
                if trade_date and len(trade_date) == 8:
                    # 格式: YYYYMMDD
                    date_time = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
                    if trade_time:
                        date_time += f" {trade_time}"
                else:
                    date_time = trade_date
            
            # 判斷買賣方向
            quantity = float(row.get('Quantity', 0))
            buy_sell = str(row.get('Buy/Sell', ''))
            if buy_sell.upper() == 'SELL' or quantity < 0:
                quantity = -abs(quantity)
            else:
                quantity = abs(quantity)
            
            trade_data = {
                'symbol': str(row.get('Symbol', '')),
                'date_time': date_time,
                'quantity': quantity,
                'price': float(row.get('TradePrice', row.get('Price', 0))),
                'proceeds': float(row.get('Proceeds', 0)),
                'commission': float(row.get('IBCommission', row.get('Commission', 0))),
                'net_cash': float(row.get('NetCash', 0)),
                'asset_category': str(row.get('AssetClass', 'STK')),
                'description': str(row.get('Description', '')),
                # 選擇權相關欄位
                'put_call': str(row.get('Put/Call', '')),
                'strike': str(row.get('Strike', '')),
                'expiry': str(row.get('Expiry', '')),
                'multiplier': str(row.get('Multiplier', '1')),
                'underlying': str(row.get('UnderlyingSymbol', '')),
                # 損益欄位（如果有）
                'realized_pnl': float(row.get('FifoPnlRealized', row.get('RealizedPnL', 0))),
            }
            trades.append(trade_data)
        
        return trades

    def _parse_trades_xml(self, xml_content: str) -> List[Dict]:
        """
        解析交易記錄 XML

        Args:
            xml_content: Flex Query 回傳的 XML

        Returns:
            trades: 交易記錄列表
        """
        root = ET.fromstring(xml_content)
        trades = []

        # 解析 Trades
        for trade in root.findall('.//Trade'):
            trade_data = {
                'symbol': trade.get('symbol'),
                'date_time': trade.get('dateTime'),
                'quantity': float(trade.get('quantity', 0)),
                'price': float(trade.get('tradePrice', 0)),
                'proceeds': float(trade.get('proceeds', 0)),
                'commission': float(trade.get('commission', 0)),
                'net_cash': float(trade.get('netCash', 0)),
                'asset_category': trade.get('assetCategory', 'STK'),
                'description': trade.get('description', ''),
                # 選擇權相關欄位
                'put_call': trade.get('putCall'),
                'strike': trade.get('strike'),
                'expiry': trade.get('expiry'),
                'multiplier': trade.get('multiplier', '1'),
            }
            trades.append(trade_data)

        return trades

    def _parse_positions_xml(self, xml_content: str) -> List[Dict]:
        """
        解析庫存快照 XML

        Args:
            xml_content: Flex Query 回傳的 XML

        Returns:
            positions: 庫存列表
        """
        root = ET.fromstring(xml_content)
        positions = []

        # 解析 OpenPositions
        for position in root.findall('.//OpenPosition'):
            position_data = {
                'symbol': position.get('symbol'),
                'position': float(position.get('position', 0)),
                'mark_price': float(position.get('markPrice', 0)),
                'average_cost': float(position.get('costBasisPrice', 0)),
                'unrealized_pnl': float(position.get('fifoPnlUnrealized', 0)),
                'asset_category': position.get('assetCategory', 'STK'),
                'description': position.get('description', ''),
                # 選擇權相關欄位
                'put_call': position.get('putCall'),
                'strike': position.get('strike'),
                'expiry': position.get('expiry'),
                'multiplier': position.get('multiplier', '1'),
            }
            positions.append(position_data)

        return positions

    def get_trades(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        取得交易記錄

        Args:
            date: 日期（YYYY-MM-DD），預設為昨天

        Returns:
            trades_df: 交易記錄 DataFrame
        """
        if not self.trades_query_id:
            raise ValueError("IBKR_TRADES_QUERY_ID 未設定")

        # Step 1: 請求生成報表
        reference_code = self._request_report(self.trades_query_id)

        # Step 2: 取得報表
        content = self._get_report(reference_code)

        # Step 3: 偵測格式並解析
        format_type = self._detect_format(content)
        if format_type == 'csv':
            trades = self._parse_trades_csv(content)
        else:
            trades = self._parse_trades_xml(content)

        if not trades:
            return pd.DataFrame()

        df = pd.DataFrame(trades)

        # 日期篩選
        if date and 'date_time' in df.columns:
            df['date'] = pd.to_datetime(df['date_time'], errors='coerce').dt.date.astype(str)
            df = df[df['date'] == date]

        return df

    def get_positions(self) -> pd.DataFrame:
        """
        取得當前庫存快照

        Returns:
            positions_df: 庫存 DataFrame
        """
        if not self.positions_query_id:
            raise ValueError("IBKR_POSITIONS_QUERY_ID 未設定")

        # Step 1: 請求生成報表
        reference_code = self._request_report(self.positions_query_id)

        # Step 2: 取得報表
        xml_content = self._get_report(reference_code)

        # Step 3: 解析 XML
        positions = self._parse_positions_xml(xml_content)

        if not positions:
            return pd.DataFrame()

        return pd.DataFrame(positions)

    def sync_to_database(self, db) -> Dict[str, int]:
        """
        同步交易記錄和庫存到資料庫

        Args:
            db: Database 實例

        Returns:
            result: {'trades': count, 'positions': count}
        """
        result = {'trades': 0, 'positions': 0}

        # 1. 同步前一日交易記錄
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            trades_df = self.get_trades(date=yesterday)

            if not trades_df.empty:
                # 轉換為資料庫格式
                trades_to_import = []
                for _, row in trades_df.iterrows():
                    trade = {
                        'date': pd.to_datetime(row['date_time']).strftime('%Y-%m-%d'),
                        'symbol': row['symbol'],
                        'quantity': row['quantity'],
                        'price': row['price'],
                        'proceeds': row['proceeds'],
                        'comm_fee': row['commission'],
                        'asset_category': row['asset_category'],
                        'description': row['description'],
                    }
                    trades_to_import.append(trade)

                result['trades'] = db.batch_insert_trades(trades_to_import)

        except Exception as e:
            print(f"同步交易記錄失敗: {str(e)}")

        # 2. 同步當前庫存快照
        try:
            positions_df = self.get_positions()

            if not positions_df.empty:
                # 轉換為資料庫格式
                positions_to_import = []
                today = datetime.now().strftime('%Y-%m-%d')

                for _, row in positions_df.iterrows():
                    position = {
                        'symbol': row['symbol'],
                        'position': row['position'],
                        'mark_price': row['mark_price'],
                        'average_cost': row['average_cost'],
                        'unrealized_pnl': row['unrealized_pnl'],
                        'instrument_type': 'option' if row['asset_category'] == 'OPT' else 'stock',
                    }

                    # 選擇權額外欄位
                    if row['asset_category'] == 'OPT':
                        position.update({
                            'strike': float(row['strike']) if row['strike'] else None,
                            'expiry': row['expiry'],
                            'option_type': 'Call' if row['put_call'] == 'C' else 'Put',
                            'multiplier': int(row['multiplier']),
                            'underlying': row['symbol'].split()[0] if ' ' in row['symbol'] else row['symbol']
                        })

                    positions_to_import.append(position)

                result['positions'] = db.upsert_open_positions(positions_to_import, snapshot_date=today)

        except Exception as e:
            print(f"同步庫存快照失敗: {str(e)}")

        return result


# 測試用
if __name__ == "__main__":
    flex = IBKRFlexQuery()

    print("=== 測試取得交易記錄 ===")
    trades = flex.get_trades()
    print(f"取得 {len(trades)} 筆交易")
    print(trades.head())

    print("\n=== 測試取得庫存快照 ===")
    positions = flex.get_positions()
    print(f"取得 {len(positions)} 個部位")
    print(positions.head())
