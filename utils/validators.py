"""
資料驗證模組

提供各種資料驗證功能
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import pandas as pd


def safe_float(value: Any, default: float = 0.0, allow_negative: bool = True) -> float:
    """
    安全地將值轉換為 float
    
    處理 IBKR 可能返回的各種異常情況：
    - None, NaN, 空字串
    - 無法解析的字串
    - 可選的負值處理
    
    Args:
        value: 要轉換的值
        default: 轉換失敗時的預設值
        allow_negative: 是否允許負值（False 時取絕對值）
        
    Returns:
        float: 轉換後的數值
    """
    if value is None:
        return default
    
    if isinstance(value, str):
        value = value.strip()
        if value == '' or value.lower() in ['nan', 'none', 'null', '-', '--']:
            return default
    
    try:
        result = float(value)
        
        # 檢查 NaN
        if pd.isna(result):
            return default
        
        # 處理負值
        if not allow_negative and result < 0:
            return abs(result)
        
        return result
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0, allow_negative: bool = True) -> int:
    """
    安全地將值轉換為 int
    
    Args:
        value: 要轉換的值
        default: 轉換失敗時的預設值
        allow_negative: 是否允許負值
        
    Returns:
        int: 轉換後的整數
    """
    result = safe_float(value, float(default), allow_negative)
    return int(result)


def safe_date_parse(date_str: Any, formats: Optional[List[str]] = None) -> Optional[str]:
    """
    安全地解析日期字串並返回標準格式 (YYYY-MM-DD)
    
    處理 IBKR 的多種日期格式：
    - YYYYMMDD
    - YYYY-MM-DD
    - YYYYMMDD;HHMMSS
    - YYYY/MM/DD
    
    Args:
        date_str: 日期字串
        formats: 自定義格式列表
        
    Returns:
        標準格式的日期字串，或 None
    """
    if date_str is None:
        return None
    
    date_str = str(date_str).strip()
    if not date_str or date_str.lower() in ['nan', 'none', 'null']:
        return None
    
    # 處理帶有時間的格式 (YYYYMMDD;HHMMSS)
    if ';' in date_str:
        date_str = date_str.split(';')[0]
    
    # 嘗試的格式列表
    if formats is None:
        formats = [
            '%Y%m%d',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y%m%d%H%M%S',
        ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str[:len(fmt.replace('%Y', 'YYYY').replace('%m', 'MM').replace('%d', 'DD').replace('%H', 'HH').replace('%M', 'MM').replace('%S', 'SS'))], fmt)
            return parsed.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    
    # 處理純數字 8 位格式 (YYYYMMDD)
    if len(date_str) >= 8 and date_str[:8].isdigit():
        try:
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
        except:
            pass
    
    return None


class TradeValidator:
    """交易資料驗證器"""

    # 有效的動作類型
    VALID_ACTIONS = {'BUY', 'SELL', 'BOT', 'SLD'}

    # 有效的標的類型
    VALID_INSTRUMENT_TYPES = {'stock', 'option', 'futures'}

    @staticmethod
    def validate_trade(trade: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        驗證單筆交易資料

        Args:
            trade: 交易資料字典

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        # 1. 必要欄位檢查
        required_fields = ['datetime', 'symbol', 'action', 'quantity', 'price']
        for field in required_fields:
            if field not in trade or trade[field] is None or trade[field] == '':
                errors.append(f"缺少必要欄位: {field}")

        # 2. 數值驗證
        if 'price' in trade:
            try:
                price = float(trade['price'])
                if price < 0:
                    errors.append(f"價格不可為負數，當前: {price}")
                elif price == 0:
                    errors.append(f"價格不可為零")
            except (ValueError, TypeError):
                errors.append(f"無效的價格格式: {trade['price']}")

        if 'quantity' in trade:
            try:
                qty = float(trade['quantity'])
                if qty == 0:
                    errors.append(f"數量不可為 0")
                # 允許負數數量（代表賣出），後續處理會取絕對值
            except (ValueError, TypeError):
                errors.append(f"無效的數量格式: {trade['quantity']}")

        if 'commission' in trade and trade['commission'] is not None:
            try:
                commission = float(trade['commission'])
                # 允許負數手續費（某些券商格式），後續處理會取絕對值
            except (ValueError, TypeError):
                errors.append(f"無效的手續費格式: {trade['commission']}")

        # 3. 動作類型驗證
        if 'action' in trade:
            action = str(trade['action']).upper()
            if action not in TradeValidator.VALID_ACTIONS:
                errors.append(
                    f"無效的動作類型: {action}，有效值: {', '.join(TradeValidator.VALID_ACTIONS)}"
                )

        # 4. 標的類型驗證
        if 'instrument_type' in trade:
            itype = str(trade['instrument_type']).lower()
            if itype not in TradeValidator.VALID_INSTRUMENT_TYPES:
                errors.append(
                    f"無效的標的類型: {itype}，有效值: {', '.join(TradeValidator.VALID_INSTRUMENT_TYPES)}"
                )

        # 5. Multiplier 驗證
        if 'instrument_type' in trade and 'multiplier' in trade:
            itype = str(trade['instrument_type']).lower()
            mult = trade.get('multiplier')

            if mult is not None:
                try:
                    mult = int(mult)
                    if itype == 'option' and mult != 100:
                        errors.append(
                            f"選擇權 multiplier 應為 100，當前: {mult}（將自動修正）"
                        )
                    elif itype == 'stock' and mult != 1:
                        errors.append(
                            f"股票 multiplier 應為 1，當前: {mult}（將自動修正）"
                        )
                except (ValueError, TypeError):
                    errors.append(f"無效的 multiplier 格式: {mult}")

        # 6. 日期格式驗證
        if 'datetime' in trade and trade['datetime']:
            try:
                # 嘗試多種日期格式
                date_str = str(trade['datetime'])
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
                    try:
                        datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
                else:
                    errors.append(f"無法解析日期格式: {date_str}")
            except Exception as e:
                errors.append(f"日期驗證失敗: {str(e)}")

        # 7. 選擇權特定欄位驗證
        if trade.get('instrument_type') == 'option':
            if 'strike' in trade and trade['strike'] is not None:
                try:
                    strike = float(trade['strike'])
                    if strike <= 0:
                        errors.append(f"履約價必須大於 0，當前: {strike}")
                except (ValueError, TypeError):
                    errors.append(f"無效的履約價格式: {trade['strike']}")

            if 'option_type' in trade and trade['option_type']:
                opt_type = str(trade['option_type']).upper()
                if opt_type not in ['CALL', 'PUT', 'C', 'P']:
                    errors.append(f"無效的選擇權類型: {opt_type}")

        return (len(errors) == 0, errors)

    @staticmethod
    def auto_fix_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動修正交易資料中的常見問題

        Args:
            trade: 原始交易資料

        Returns:
            修正後的交易資料
        """
        fixed_trade = trade.copy()

        # 修正 multiplier
        if 'instrument_type' in fixed_trade and 'multiplier' in fixed_trade:
            itype = str(fixed_trade['instrument_type']).lower()

            if itype == 'option' and fixed_trade['multiplier'] != 100:
                logging.info(
                    f"Auto-fixing option multiplier: {fixed_trade['multiplier']} -> 100 for {fixed_trade.get('symbol')}"
                )
                fixed_trade['multiplier'] = 100

            elif itype == 'stock' and fixed_trade['multiplier'] != 1:
                logging.info(
                    f"Auto-fixing stock multiplier: {fixed_trade['multiplier']} -> 1 for {fixed_trade.get('symbol')}"
                )
                fixed_trade['multiplier'] = 1

        # 標準化動作名稱
        if 'action' in fixed_trade:
            action = str(fixed_trade['action']).upper()
            if action in ['BOT']:
                fixed_trade['action'] = 'BUY'
            elif action in ['SLD']:
                fixed_trade['action'] = 'SELL'

        # 標準化選擇權類型
        if 'option_type' in fixed_trade and fixed_trade['option_type']:
            opt_type = str(fixed_trade['option_type']).upper()
            if opt_type == 'C':
                fixed_trade['option_type'] = 'Call'
            elif opt_type == 'P':
                fixed_trade['option_type'] = 'Put'

        return fixed_trade

    @staticmethod
    def validate_batch(trades: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """
        批次驗證交易資料

        Args:
            trades: 交易資料列表

        Returns:
            (有效的交易列表, 無效的交易列表)
        """
        valid_trades = []
        invalid_trades = []

        for i, trade in enumerate(trades):
            is_valid, errors = TradeValidator.validate_trade(trade)

            if is_valid:
                # 自動修正
                fixed_trade = TradeValidator.auto_fix_trade(trade)
                valid_trades.append(fixed_trade)
            else:
                invalid_trades.append({
                    'index': i,
                    'trade': trade,
                    'errors': errors
                })
                logging.warning(f"Invalid trade at index {i}: {', '.join(errors)}")

        return valid_trades, invalid_trades


class DataFrameValidator:
    """DataFrame 資料驗證器"""

    @staticmethod
    def validate_trades_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        驗證交易 DataFrame

        Args:
            df: 交易 DataFrame

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        # 檢查是否為空
        if df.empty:
            errors.append("DataFrame 為空")
            return False, errors

        # 檢查必要欄位
        required_columns = ['datetime', 'symbol', 'action', 'quantity', 'price']
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            errors.append(f"缺少必要欄位: {', '.join(missing_cols)}")

        # 檢查資料類型
        if 'quantity' in df.columns:
            non_numeric = df[~df['quantity'].apply(lambda x: isinstance(x, (int, float)))]['quantity']
            if len(non_numeric) > 0:
                errors.append(f"發現 {len(non_numeric)} 筆非數值的數量資料")

        if 'price' in df.columns:
            non_numeric = df[~df['price'].apply(lambda x: isinstance(x, (int, float)))]['price']
            if len(non_numeric) > 0:
                errors.append(f"發現 {len(non_numeric)} 筆非數值的價格資料")

        # 檢查重複記錄
        if not df.empty and all(col in df.columns for col in required_columns):
            duplicates = df.duplicated(subset=required_columns, keep=False)
            if duplicates.sum() > 0:
                errors.append(f"發現 {duplicates.sum()} 筆可能重複的記錄")

        return (len(errors) == 0, errors)
