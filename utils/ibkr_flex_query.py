"""
IBKR Flex Query 整合模組

透過 IBKR Flex Web Service API 自動取得交易記錄和庫存快照
文件：https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm
"""

import os
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FlexQueryValidationResult:
    """Flex Query 驗證結果"""
    is_valid: bool
    query_id: str
    query_type: str  # 'trades', 'positions', 'history'
    missing_fields: List[str]
    extra_fields: List[str]
    warnings: List[str]
    sample_data: Optional[pd.DataFrame] = None

    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'query_id': self.query_id,
            'query_type': self.query_type,
            'missing_fields': self.missing_fields,
            'extra_fields': self.extra_fields,
            'warnings': self.warnings,
        }


class FlexQueryValidator:
    """
    Flex Query 欄位驗證器
    
    確保用戶的 Flex Query 配置包含必要欄位，以便正確匯入交易資料
    """
    
    # 三種 Query 的必要欄位定義（基於用戶的截圖配置）
    REQUIRED_FIELDS = {
        # 1Year_History_Import (Query ID: 1344117) - 完整歷史交易
        'history': {
            'required': [
                'Symbol', 'TradeDate', 'Quantity', 'TradePrice', 
                'IBCommission', 'AssetClass', 'Buy/Sell'
            ],
            'optional': [
                'DateTime', 'Description', 'Proceeds', 'Strike', 'Expiry',
                'Put/Call', 'Multiplier', 'UnderlyingSymbol', 'FifoPnlRealized',
                'Exchange', 'TradeID', 'Conid', 'FXRateToBase'
            ],
            'description': '歷史交易記錄（用於 AI 分析）'
        },
        # n8n_Day_Trade (Query ID: 1336451) - 每日交易
        'trades': {
            'required': [
                'Symbol', 'TradeDate', 'Quantity', 'TradePrice',
                'IBCommission', 'AssetClass', 'Buy/Sell'
            ],
            'optional': [
                'Strike', 'Expiry', 'Put/Call', 'Multiplier', 'UnderlyingSymbol'
            ],
            'description': '每日交易記錄（增量匯入）'
        },
        # n8n_Postions_Snapshot (Query ID: 1337233) - 持倉快照
        'positions': {
            'required': [
                'Symbol', 'Quantity', 'MarkPrice', 'CostBasisPrice',
                'AssetClass'
            ],
            'optional': [
                'Strike', 'Expiry', 'Put/Call', 'Multiplier', 
                'UnderlyingSymbol', 'FifoPnlUnrealized', 'PositionValue',
                'CostBasisMoney', 'LevelOfDetail'
            ],
            'description': '當前持倉快照（未平倉部位）'
        }
    }
    
    # 欄位名稱別名映射（IBKR 可能使用不同的欄位名稱）
    FIELD_ALIASES = {
        'TradeDate': ['Date', 'Trade Date', 'TradeDate'],
        'TradePrice': ['Price', 'Trade Price', 'TradePrice'],
        'IBCommission': ['Commission', 'Comm/Fee', 'IBCommission'],
        'Buy/Sell': ['Side', 'B/S', 'Buy/Sell', 'TransactionType'],
        'Put/Call': ['Right', 'Option Type', 'Put/Call'],
        'MarkPrice': ['Mark Price', 'MarkPrice', 'Price'],
        'CostBasisPrice': ['Avg Cost', 'Average Cost', 'CostBasisPrice'],
        'FifoPnlUnrealized': ['Unrealized P/L', 'UnrealizedPnL', 'FifoPnlUnrealized'],
    }

    @classmethod
    def validate_dataframe(
        cls,
        df: pd.DataFrame,
        query_type: str,
        query_id: str = ''
    ) -> FlexQueryValidationResult:
        """
        驗證 DataFrame 是否包含必要欄位
        
        Args:
            df: 從 Flex Query 取得的 DataFrame
            query_type: 'trades', 'positions', 或 'history'
            query_id: Query ID（用於錯誤訊息）
            
        Returns:
            FlexQueryValidationResult
        """
        if query_type not in cls.REQUIRED_FIELDS:
            return FlexQueryValidationResult(
                is_valid=False,
                query_id=query_id,
                query_type=query_type,
                missing_fields=[],
                extra_fields=[],
                warnings=[f"未知的 Query 類型: {query_type}"]
            )
        
        schema = cls.REQUIRED_FIELDS[query_type]
        df_columns = set(df.columns.tolist())
        
        # 檢查必要欄位（考慮別名）
        missing_fields = []
        for field in schema['required']:
            aliases = cls.FIELD_ALIASES.get(field, [field])
            if not any(alias in df_columns for alias in aliases):
                missing_fields.append(field)
        
        # 檢查額外欄位（可能有用但非必要）
        all_known_fields = set(schema['required'] + schema['optional'])
        for field, aliases in cls.FIELD_ALIASES.items():
            all_known_fields.update(aliases)
        
        extra_fields = [col for col in df_columns if col not in all_known_fields]
        
        # 生成警告
        warnings = []
        if missing_fields:
            warnings.append(
                f"缺少必要欄位將導致資料匯入不完整。"
                f"請在 IBKR Flex Query 設定中加入這些欄位。"
            )
        
        # 檢查選擇權相關欄位
        if query_type in ['trades', 'history']:
            option_fields = ['Strike', 'Expiry', 'Put/Call']
            missing_option = [f for f in option_fields if f not in df_columns]
            if missing_option and 'AssetClass' in df_columns:
                if 'OPT' in df['AssetClass'].values:
                    warnings.append(
                        f"偵測到選擇權交易，但缺少欄位: {', '.join(missing_option)}。"
                        f"這將影響選擇權策略識別。"
                    )
        
        is_valid = len(missing_fields) == 0
        
        return FlexQueryValidationResult(
            is_valid=is_valid,
            query_id=query_id,
            query_type=query_type,
            missing_fields=missing_fields,
            extra_fields=extra_fields[:10],  # 限制數量
            warnings=warnings,
            sample_data=df.head(3) if not df.empty else None
        )

    @classmethod
    def get_setup_instructions(cls, query_type: str) -> str:
        """
        取得 Flex Query 設定指南
        
        Args:
            query_type: 'trades', 'positions', 或 'history'
            
        Returns:
            設定指南文字
        """
        if query_type not in cls.REQUIRED_FIELDS:
            return "未知的 Query 類型"
        
        schema = cls.REQUIRED_FIELDS[query_type]
        
        instructions = f"""
## {schema['description']} 設定指南

### 必要欄位（Required）
請確保您的 Flex Query 包含以下欄位：
{chr(10).join(f'- {field}' for field in schema['required'])}

### 建議欄位（Optional）
以下欄位可提供更完整的分析：
{chr(10).join(f'- {field}' for field in schema['optional'])}

### 設定步驟
1. 登入 IBKR Portal
2. 前往 Settings > Account Settings > Flex Web Service
3. 建立或編輯 Flex Query
4. 在「Sections」中選擇對應的區段（Trades 或 Open Positions）
5. 勾選上述必要欄位
6. 儲存並記下 Query ID
"""
        return instructions


class IBKRFlexQuery:
    """IBKR Flex Query API 客戶端"""

    BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet"

    def __init__(
        self,
        token: Optional[str] = None,
        history_query_id: Optional[str] = None,
        positions_query_id: Optional[str] = None,
    ):
        """初始化 Flex Query 客戶端"""
        self.token = token or os.getenv('IBKR_FLEX_TOKEN')
        self.history_query_id = history_query_id or os.getenv('IBKR_HISTORY_QUERY_ID')
        self.positions_query_id = positions_query_id or os.getenv('IBKR_POSITIONS_QUERY_ID')

        if not self.token:
            raise ValueError("IBKR_FLEX_TOKEN 未設定，請在 .env 檔案中配置")

        self.session = requests.Session()

    def validate_query(
        self,
        query_id: str,
        query_type: str,
        timeout: int = 60
    ) -> FlexQueryValidationResult:
        """
        驗證 Flex Query 配置是否正確
        
        透過實際呼叫 IBKR API 取得樣本資料，驗證欄位是否符合需求
        
        Args:
            query_id: Flex Query ID
            query_type: 'trades', 'positions', 或 'history'
            timeout: 等待報表生成的超時時間（秒）
            
        Returns:
            FlexQueryValidationResult
        """
        import time
        
        try:
            # Step 1: 請求生成報表
            reference_code = self._request_report(query_id)
            
            # Step 2: 等待報表生成（歷史報表較大需要更長時間）
            wait_time = 15 if query_type == 'history' else 5
            time.sleep(wait_time)
            
            # Step 3: 取得報表
            content = self._get_report(reference_code)
            
            # Step 4: 解析為 DataFrame
            format_type = self._detect_format(content)
            if format_type == 'csv':
                from io import StringIO
                df = pd.read_csv(StringIO(content))
            else:
                # XML 格式需要特殊處理
                if query_type == 'positions':
                    positions = self._parse_positions_xml(content)
                    df = pd.DataFrame(positions) if positions else pd.DataFrame()
                else:
                    trades = self._parse_trades_xml(content)
                    df = pd.DataFrame(trades) if trades else pd.DataFrame()
            
            # Step 5: 驗證欄位
            return FlexQueryValidator.validate_dataframe(df, query_type, query_id)
            
        except Exception as e:
            return FlexQueryValidationResult(
                is_valid=False,
                query_id=query_id,
                query_type=query_type,
                missing_fields=[],
                extra_fields=[],
                warnings=[f"API 請求失敗: {str(e)}"]
            )

    def validate_all_queries(self) -> Dict[str, FlexQueryValidationResult]:
        """
        驗證所有已配置的 Flex Query
        
        Returns:
            Dict[query_type, FlexQueryValidationResult]
        """
        results = {}
        
        # 驗證歷史交易記錄 Query
        if self.history_query_id:
            results['history'] = self.validate_query(
                self.history_query_id, 'history'
            )
        
        # 驗證持倉快照 Query
        if self.positions_query_id:
            results['positions'] = self.validate_query(
                self.positions_query_id, 'positions'
            )
        
        # 驗證歷史交易 Query
        history_query_id = os.getenv('IBKR_HISTORY_QUERY_ID')
        if history_query_id:
            results['history'] = self.validate_query(
                history_query_id, 'history'
            )
        
        return results

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

    def _parse_cash_report_xml(self, xml_content: str) -> List[Dict]:
        """
        解析現金報表 XML
        
        Args:
            xml_content: Flex Query 回傳的 XML
            
        Returns:
            cash_reports: 現金報表列表（按幣別）
        """
        root = ET.fromstring(xml_content)
        cash_reports = []
        
        # 解析 CashReport
        for cash in root.findall('.//CashReport'):
            cash_data = {
                'currency': cash.get('currency', 'USD'),
                'starting_cash': float(cash.get('startingCash', 0)),
                'ending_cash': float(cash.get('endingCash', 0)),
                'ending_settled_cash': float(cash.get('endingSettledCash', 0)),
                'deposits': float(cash.get('deposits', 0)),
                'withdrawals': float(cash.get('withdrawals', 0)),
                'deposits_withdrawals': float(cash.get('depositsWithdrawals', 0)),
                'dividends': float(cash.get('dividends', 0)),
                'broker_interest': float(cash.get('brokerInterest', 0)),
                'net_trades_sales': float(cash.get('netTradesSales', 0)),
                'net_trades_purchases': float(cash.get('netTradesPurchases', 0)),
                'commissions': float(cash.get('commissions', 0)),
                'other_fees': float(cash.get('otherFees', 0)),
                'from_date': cash.get('fromDate', ''),
                'to_date': cash.get('toDate', ''),
            }
            cash_reports.append(cash_data)
        
        return cash_reports

    def get_cash_balance(self, query_id: Optional[str] = None) -> Dict:
        """
        取得現金庫存
        
        Args:
            query_id: Flex Query ID（預設使用 IBKR_HISTORY_QUERY_ID）
            
        Returns:
            cash_balance: 現金庫存資訊
        """
        import time
        
        # 使用指定的 query_id 或預設值
        qid = query_id or self.history_query_id
        if not qid:
            raise ValueError("未設定 Query ID")
        
        # Step 1: 請求生成報表
        reference_code = self._request_report(qid)
        
        # Step 2: 等待報表生成
        time.sleep(5)
        
        # Step 3: 取得報表
        content = self._get_report(reference_code)
        
        # Step 4: 解析現金報表
        format_type = self._detect_format(content)
        
        if format_type == 'xml':
            cash_reports = self._parse_cash_report_xml(content)
        else:
            # CSV 格式需要特殊處理
            cash_reports = self._parse_cash_report_csv(content)
        
        if not cash_reports:
            return {'error': '無現金報表資料，請確認 Flex Query 已勾選 Cash Report 區段'}
        
        # 整理結果
        total_cash = sum(c.get('ending_cash', 0) for c in cash_reports)
        total_settled = sum(c.get('ending_settled_cash', 0) for c in cash_reports)
        
        return {
            'total_cash': total_cash,
            'total_settled_cash': total_settled,
            'by_currency': cash_reports,
            'last_updated': datetime.now().isoformat(),
        }

    def _parse_cash_report_csv(self, csv_content: str) -> List[Dict]:
        """
        解析現金報表 CSV
        """
        from io import StringIO
        
        try:
            df = pd.read_csv(StringIO(csv_content))
        except Exception:
            return []
        
        # 尋找 Cash Report 相關欄位
        cash_columns = ['Currency', 'EndingCash', 'EndingSettledCash', 'StartingCash']
        if not any(col in df.columns for col in cash_columns):
            return []
        
        cash_reports = []
        for _, row in df.iterrows():
            if 'Currency' in row and pd.notna(row.get('Currency')):
                cash_data = {
                    'currency': str(row.get('Currency', 'USD')),
                    'starting_cash': float(row.get('StartingCash', 0)),
                    'ending_cash': float(row.get('EndingCash', 0)),
                    'ending_settled_cash': float(row.get('EndingSettledCash', 0)),
                }
                cash_reports.append(cash_data)
        
        return cash_reports

    def get_trades(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        取得交易記錄

        Args:
            date: 日期（YYYY-MM-DD），預設為昨天

        Returns:
            trades_df: 交易記錄 DataFrame
        """
        if not self.history_query_id:
            raise ValueError("IBKR_HISTORY_QUERY_ID 未設定")

        # Step 1: 請求生成報表
        reference_code = self._request_report(self.history_query_id)

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
        import time
        
        if not self.positions_query_id:
            raise ValueError("IBKR_POSITIONS_QUERY_ID 未設定")

        # Step 1: 請求生成報表
        reference_code = self._request_report(self.positions_query_id)

        # Step 2: 等待報表生成
        time.sleep(5)

        # Step 3: 取得報表
        content = self._get_report(reference_code)

        # Step 4: 偵測格式並解析
        format_type = self._detect_format(content)
        
        if format_type == 'csv':
            positions = self._parse_positions_csv(content)
        else:
            positions = self._parse_positions_xml(content)

        if not positions:
            return pd.DataFrame()

        return pd.DataFrame(positions)

    def _parse_positions_csv(self, csv_content: str) -> List[Dict]:
        """
        解析庫存快照 CSV（IBKR Flex Query 特殊格式）

        Args:
            csv_content: Flex Query 回傳的 CSV

        Returns:
            positions: 庫存列表
        """
        from io import StringIO
        
        # IBKR CSV 格式有多種行類型：BOF, BOA, BOS, EOS, EOA, EOF
        # 只處理以 "STK" 或 "OPT" 開頭的數據行
        lines = csv_content.strip().split('\n')
        
        # 找到 header 行（包含 AssetClass）
        header_idx = None
        for i, line in enumerate(lines):
            if line.startswith('"AssetClass"') or line.startswith('AssetClass'):
                header_idx = i
                break
        
        if header_idx is None:
            # 嘗試使用標準 CSV 解析
            try:
                df = pd.read_csv(StringIO(csv_content))
                positions = []
                for _, row in df.iterrows():
                    if 'Symbol' not in row or pd.isna(row.get('Symbol')):
                        continue
                    position_data = {
                        'symbol': str(row.get('Symbol', '')),
                        'position': float(row.get('Position', row.get('Quantity', 0))),
                        'mark_price': float(row.get('MarkPrice', row.get('Mark', 0))),
                        'average_cost': float(row.get('CostBasisPrice', row.get('AvgCost', 0))),
                        'unrealized_pnl': float(row.get('FifoPnlUnrealized', row.get('UnrealizedP/L', 0))),
                        'asset_category': str(row.get('AssetClass', 'STK')),
                        'description': str(row.get('Description', '')),
                        'put_call': str(row.get('Put/Call', '')),
                        'strike': str(row.get('Strike', '')),
                        'expiry': str(row.get('Expiry', '')),
                        'multiplier': str(row.get('Multiplier', '1')),
                    }
                    positions.append(position_data)
                return positions
            except Exception:
                return []
        
        # 解析 header
        header_line = lines[header_idx]
        headers = [h.strip().strip('"') for h in header_line.split(',')]
        
        positions = []
        
        # 解析數據行（從 header 之後開始）
        for line in lines[header_idx + 1:]:
            # 跳過 IBKR 報表控制行 (BOF, BOA, BOS, EOS, EOA, EOF)
            if line.startswith('"BO') or line.startswith('"EO'):
                continue
            
            # 放寬資產類別檢查，支援更多類型 (STK, OPT, IOPT, FUT, FOP, IND, etc.)
            # 如果行首不是常見資產類別，可能需要檢查是否為有效數據行
            if not any(line.startswith(f'"{prefix}') for prefix in ['STK', 'OPT', 'IOPT', 'FUT', 'FOP', 'IND', 'WAR', 'CASH']):
                # 如果不是上述類型，但看起來像數據行（包含多個逗號），也嘗試解析
                if line.count(',') < 5:
                    continue
            
            # 解析 CSV 行
            values = []
            in_quote = False
            current = ''
            for char in line:
                if char == '"':
                    in_quote = not in_quote
                elif char == ',' and not in_quote:
                    values.append(current.strip().strip('"'))
                    current = ''
                else:
                    current += char
            values.append(current.strip().strip('"'))  # 最後一個值
            
            # 建立字典
            row_dict = {}
            for i, h in enumerate(headers):
                if i < len(values):
                    row_dict[h] = values[i]
            
            # 轉換為 position_data
            try:
                position_data = {
                    'symbol': row_dict.get('Symbol', ''),
                    'position': float(row_dict.get('Quantity', 0)),
                    'mark_price': float(row_dict.get('MarkPrice', 0)),
                    'average_cost': float(row_dict.get('CostBasisPrice', 0)),
                    'unrealized_pnl': float(row_dict.get('FifoPnlUnrealized', 0)),
                    'asset_category': row_dict.get('AssetClass', 'STK'),
                    'description': '',
                    'put_call': row_dict.get('Put/Call', ''),
                    'strike': row_dict.get('Strike', ''),
                    'expiry': row_dict.get('Expiry', ''),
                    'multiplier': row_dict.get('Multiplier', '1'),
                }
                positions.append(position_data)
            except (ValueError, KeyError) as e:
                print(f"解析行失敗: {line}, 錯誤: {e}")
                continue
        
        return positions


    def get_historical_trades(
        self,
        query_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        取得歷史交易記錄（過去一年）

        Args:
            query_id: 自訂的 Flex Query ID，預設使用環境變數 IBKR_HISTORY_QUERY_ID
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            symbol: 篩選特定標的

        Returns:
            trades_df: 歷史交易記錄 DataFrame
        """
        # 使用提供的 query_id 或環境變數
        history_query_id = query_id or os.getenv('IBKR_HISTORY_QUERY_ID')
        
        if not history_query_id:
            raise ValueError("請提供 query_id 或設定 IBKR_HISTORY_QUERY_ID 環境變數")

        import time
        
        # Step 1: 請求生成報表
        reference_code = self._request_report(history_query_id)

        # Step 2: 等待報表生成（歷史報表較大，需要等待）
        time.sleep(15)

        # Step 3: 取得報表
        content = self._get_report(reference_code)

        # Step 4: 偵測格式並解析
        format_type = self._detect_format(content)
        if format_type == 'csv':
            trades = self._parse_historical_trades_csv(content)
        else:
            trades = self._parse_trades_xml(content)

        if not trades:
            return pd.DataFrame()

        df = pd.DataFrame(trades)

        # 日期篩選
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
            
            if start_date:
                df = df[df['trade_date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['trade_date'] <= pd.to_datetime(end_date)]

        # 標的篩選
        if symbol and 'symbol' in df.columns:
            df = df[df['symbol'].str.upper() == symbol.upper()]

        return df

    def _parse_historical_trades_csv(self, csv_content: str) -> List[Dict]:
        """
        解析歷史交易 CSV（更詳細的格式）
        
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
            # 處理日期
            trade_date = str(row.get('TradeDate', ''))
            if trade_date and len(trade_date) == 8:
                trade_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            
            # 處理時間
            date_time = str(row.get('DateTime', ''))
            if ';' in date_time:
                parts = date_time.split(';')
                if len(parts) == 2 and len(parts[0]) == 8:
                    date_time = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:8]} {parts[1]}"
            
            # 判斷買賣方向
            quantity = float(row.get('Quantity', 0))
            buy_sell = str(row.get('Buy/Sell', ''))
            
            trade_data = {
                'trade_date': trade_date,
                'date_time': date_time,
                'symbol': str(row.get('Symbol', '')),
                'description': str(row.get('Description', '')),
                'asset_class': str(row.get('AssetClass', 'STK')),
                'buy_sell': buy_sell,
                'quantity': quantity,
                'price': float(row.get('TradePrice', 0)),
                'proceeds': float(row.get('Proceeds', 0)),
                'commission': float(row.get('IBCommission', 0)),
                'net_cash': float(row.get('NetCash', 0)),
                'realized_pnl': float(row.get('FifoPnlRealized', 0)),
                'mtm_pnl': float(row.get('MtmPnl', 0)),
                'open_close': str(row.get('Open/CloseIndicator', '')),
                'exchange': str(row.get('Exchange', '')),
                'order_type': str(row.get('OrderType', '')),
                # 選擇權相關
                'put_call': str(row.get('Put/Call', '')),
                'strike': str(row.get('Strike', '')),
                'expiry': str(row.get('Expiry', '')),
                'underlying': str(row.get('UnderlyingSymbol', '')),
            }
            trades.append(trade_data)
        
        return trades

    def get_trade_summary_for_ai(
        self,
        query_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> Dict:
        """
        取得適合 AI 分析的交易摘要
        
        Returns:
            summary: 包含統計數據和交易明細的字典
        """
        df = self.get_historical_trades(
            query_id=query_id,
            start_date=start_date,
            end_date=end_date,
            symbol=symbol
        )
        
        if df.empty:
            return {'error': '無交易記錄', 'trades': [], 'statistics': {}}
        
        # 計算統計數據
        total_trades = len(df)
        total_realized_pnl = df['realized_pnl'].sum() if 'realized_pnl' in df.columns else 0
        total_commission = df['commission'].sum() if 'commission' in df.columns else 0
        
        # 分析勝敗
        if 'realized_pnl' in df.columns:
            closed_trades = df[df['open_close'] == 'C']
            winning_trades = closed_trades[closed_trades['realized_pnl'] > 0]
            losing_trades = closed_trades[closed_trades['realized_pnl'] < 0]
            
            win_rate = len(winning_trades) / len(closed_trades) * 100 if len(closed_trades) > 0 else 0
            avg_win = winning_trades['realized_pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['realized_pnl'].mean() if len(losing_trades) > 0 else 0
        else:
            win_rate = avg_win = avg_loss = 0
        
        # 按標的分組統計
        symbol_stats = {}
        if 'symbol' in df.columns:
            for sym in df['symbol'].unique():
                sym_df = df[df['symbol'] == sym]
                sym_pnl = sym_df['realized_pnl'].sum() if 'realized_pnl' in sym_df.columns else 0
                sym_trades = len(sym_df)
                symbol_stats[sym] = {'trades': sym_trades, 'pnl': round(sym_pnl, 2)}
        
        # 準備交易明細（限制數量以控制 token）
        trades_for_ai = df.head(100).to_dict(orient='records')
        
        return {
            'period': {
                'start': start_date or df['trade_date'].min().strftime('%Y-%m-%d') if 'trade_date' in df.columns else 'N/A',
                'end': end_date or df['trade_date'].max().strftime('%Y-%m-%d') if 'trade_date' in df.columns else 'N/A',
            },
            'statistics': {
                'total_trades': total_trades,
                'total_realized_pnl': round(total_realized_pnl, 2),
                'total_commission': round(total_commission, 2),
                'win_rate': round(win_rate, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
            },
            'by_symbol': symbol_stats,
            'trades': trades_for_ai,
        }

    def sync_to_database(self, db) -> Dict[str, int]:
        """
        同步交易記錄和庫存到資料庫

        Args:
            db: Database 實例

        Returns:
            result: {'trades': count, 'positions': count}
        """
        result = {'trades': 0, 'positions': 0}

        # 1. 同步交易記錄（不篩選日期，讓 Flex Query 設定決定範圍）
        try:
            trades_df = self.get_trades()  # 取得所有交易，不篩選日期

            if not trades_df.empty:
                # 轉換為資料庫格式
                trades_to_import = []
                for _, row in trades_df.iterrows():
                    # 處理日期格式
                    date_str = str(row.get('date_time', ''))
                    if date_str:
                        try:
                            # 嘗試解析各種日期格式
                            parsed_date = pd.to_datetime(date_str, errors='coerce')
                            if pd.notna(parsed_date):
                                date_str = parsed_date.strftime('%Y%m%d')
                        except:
                            pass
                    
                    trade = {
                        'datetime': date_str,
                        'symbol': row['symbol'],
                        'action': 'BUY' if row['quantity'] > 0 else 'SELL',
                        'quantity': abs(row['quantity']),
                        'price': row['price'],
                        'commission': abs(row.get('commission', 0)),
                        'instrument_type': 'option' if row.get('asset_category') == 'OPT' else 'stock',
                        'strike': float(row['strike']) if row.get('strike') and row['strike'] != '' else None,
                        'expiry': row.get('expiry', ''),
                        'option_type': 'Call' if row.get('put_call') == 'C' else ('Put' if row.get('put_call') == 'P' else None),
                        'multiplier': int(row.get('multiplier', 1)) if row.get('multiplier') else 1,
                        'underlying': row.get('underlying', row['symbol']),
                    }
                    
                    # 使用 add_trade 方法（會自動去重）
                    if db.add_trade(trade):
                        result['trades'] += 1

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
