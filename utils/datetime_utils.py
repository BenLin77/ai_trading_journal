"""
統一日期時間處理工具

此模組負責：
1. 統一各種日期格式轉換
2. 確保與資料庫格式一致
3. 提供常用日期操作函式
"""

from datetime import datetime, timedelta
from typing import Union, Optional
import pandas as pd


class DateTimeUtils:
    """日期時間工具類"""
    
    # 資料庫標準格式
    DB_DATE_FORMAT = "%Y%m%d"
    DB_DATETIME_FORMAT = "%Y%m%d%H%M%S"
    
    # 顯示格式
    DISPLAY_DATE_FORMAT = "%Y-%m-%d"
    DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @staticmethod
    def normalize_date(date_input: Union[str, datetime, pd.Timestamp]) -> str:
        """
        統一轉換為 YYYYMMDD 格式（資料庫標準）
        
        支援格式:
        - YYYY-MM-DD
        - YYYY/MM/DD  
        - YYYYMMDD
        - datetime object
        - pandas Timestamp
        
        Args:
            date_input: 各種格式的日期輸入
            
        Returns:
            YYYYMMDD 格式字串
            
        Examples:
            >>> DateTimeUtils.normalize_date("2025-10-25")
            '20251025'
            >>> DateTimeUtils.normalize_date("2025/10/25")
            '20251025'
            >>> DateTimeUtils.normalize_date("20251025")
            '20251025'
        """
        if isinstance(date_input, str):
            # 移除所有分隔符和空格
            cleaned = date_input.replace('-', '').replace('/', '').replace(' ', '').strip()
            
            # 取前 8 位（YYYYMMDD）
            if len(cleaned) >= 8:
                return cleaned[:8]
            else:
                raise ValueError(f"無效的日期格式: {date_input}")
                
        elif isinstance(date_input, datetime):
            return date_input.strftime(DateTimeUtils.DB_DATE_FORMAT)
            
        elif isinstance(date_input, pd.Timestamp):
            return date_input.strftime(DateTimeUtils.DB_DATE_FORMAT)
            
        else:
            raise TypeError(f"不支援的日期類型: {type(date_input)}")
    
    @staticmethod
    def normalize_datetime(datetime_input: Union[str, datetime, pd.Timestamp]) -> str:
        """
        統一轉換為 YYYYMMDDHHMMSS 格式（資料庫標準）
        
        Args:
            datetime_input: 各種格式的日期時間輸入
            
        Returns:
            YYYYMMDDHHMMSS 格式字串
        """
        if isinstance(datetime_input, str):
            # 移除所有分隔符
            cleaned = datetime_input.replace('-', '').replace('/', '').replace(':', '').replace(' ', '').strip()
            
            # YYYYMMDDHHMMSS (14 位)
            if len(cleaned) >= 14:
                return cleaned[:14]
            # YYYYMMDD (8 位，補上時間 000000)
            elif len(cleaned) == 8:
                return cleaned + "000000"
            else:
                raise ValueError(f"無效的日期時間格式: {datetime_input}")
                
        elif isinstance(datetime_input, (datetime, pd.Timestamp)):
            return datetime_input.strftime(DateTimeUtils.DB_DATETIME_FORMAT)
            
        else:
            raise TypeError(f"不支援的日期時間類型: {type(datetime_input)}")
    
    @staticmethod
    def parse_db_date(db_date: str) -> datetime:
        """
        將資料庫日期格式 (YYYYMMDD) 轉回 datetime
        
        Args:
            db_date: YYYYMMDD 格式字串
            
        Returns:
            datetime 物件
        """
        return datetime.strptime(db_date, DateTimeUtils.DB_DATE_FORMAT)
    
    @staticmethod
    def parse_db_datetime(db_datetime: str) -> datetime:
        """
        將資料庫日期時間格式 (YYYYMMDDHHMMSS) 轉回 datetime
        
        Args:
            db_datetime: YYYYMMDDHHMMSS 格式字串
            
        Returns:
            datetime 物件
        """
        # 如果只有日期部分（8 位），補上時間
        if len(db_datetime) == 8:
            db_datetime += "000000"
            
        return datetime.strptime(db_datetime, DateTimeUtils.DB_DATETIME_FORMAT)
    
    @staticmethod
    def format_for_display(date_input: Union[str, datetime, pd.Timestamp], 
                          include_time: bool = False) -> str:
        """
        格式化日期以便顯示
        
        Args:
            date_input: 日期輸入（可為資料庫格式或其他格式）
            include_time: 是否包含時間部分
            
        Returns:
            使用者友善的日期字串 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)
        """
        # 先轉為 datetime
        if isinstance(date_input, str):
            if len(date_input) == 8:
                dt = DateTimeUtils.parse_db_date(date_input)
            elif len(date_input) >= 14:
                dt = DateTimeUtils.parse_db_datetime(date_input)
            else:
                # 嘗試其他格式
                dt = pd.to_datetime(date_input)
        else:
            dt = date_input
        
        # 格式化輸出
        if include_time:
            return dt.strftime(DateTimeUtils.DISPLAY_DATETIME_FORMAT)
        else:
            return dt.strftime(DateTimeUtils.DISPLAY_DATE_FORMAT)
    
    @staticmethod
    def get_date_range(start_date: str, end_date: str) -> list:
        """
        生成日期範圍列表（資料庫格式）
        
        Args:
            start_date: 開始日期（任意格式）
            end_date: 結束日期（任意格式）
            
        Returns:
            日期列表 (YYYYMMDD 格式)
        """
        start_dt = DateTimeUtils.parse_db_date(DateTimeUtils.normalize_date(start_date))
        end_dt = DateTimeUtils.parse_db_date(DateTimeUtils.normalize_date(end_date))
        
        date_list = []
        current = start_dt
        while current <= end_dt:
            date_list.append(current.strftime(DateTimeUtils.DB_DATE_FORMAT))
            current += timedelta(days=1)
        
        return date_list
    
    @staticmethod
    def is_valid_date(date_str: str) -> bool:
        """
        驗證日期字串是否有效
        
        Args:
            date_str: 日期字串
            
        Returns:
            是否為有效日期
        """
        try:
            DateTimeUtils.normalize_date(date_str)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def get_trading_days_ago(days: int, from_date: Optional[str] = None) -> str:
        """
        取得 N 個交易日前的日期（簡化版，不考慮實際市場休市）
        
        Args:
            days: 往前天數
            from_date: 起始日期（預設為今天）
            
        Returns:
            YYYYMMDD 格式日期
        """
        if from_date:
            base_date = DateTimeUtils.parse_db_date(DateTimeUtils.normalize_date(from_date))
        else:
            base_date = datetime.now()
        
        target_date = base_date - timedelta(days=days)
        return target_date.strftime(DateTimeUtils.DB_DATE_FORMAT)


# 便捷函式（簡化調用）

def normalize_date(date_input: Union[str, datetime, pd.Timestamp]) -> str:
    """快捷函式: 標準化日期"""
    return DateTimeUtils.normalize_date(date_input)


def normalize_datetime(datetime_input: Union[str, datetime, pd.Timestamp]) -> str:
    """快捷函式: 標準化日期時間"""
    return DateTimeUtils.normalize_datetime(datetime_input)


def format_for_display(date_input: Union[str, datetime, pd.Timestamp], 
                       include_time: bool = False) -> str:
    """快捷函式: 格式化顯示"""
    return DateTimeUtils.format_for_display(date_input, include_time)
