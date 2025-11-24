"""
日期工具測試

測試 utils/datetime_utils.py 的所有功能
"""

import pytest
from datetime import datetime
import pandas as pd
from utils.datetime_utils import DateTimeUtils, normalize_date, format_for_display


class TestDateTimeUtils:
    """DateTimeUtils 類別測試"""
    
    def test_normalize_date_with_dash(self):
        """測試 YYYY-MM-DD 格式"""
        result = DateTimeUtils.normalize_date("2025-10-25")
        assert result == "20251025"
    
    def test_normalize_date_with_slash(self):
        """測試 YYYY/MM/DD 格式"""
        result = DateTimeUtils.normalize_date("2025/10/25")
        assert result == "20251025"
    
    def test_normalize_date_already_normalized(self):
        """測試已經是 YYYYMMDD 格式"""
        result = DateTimeUtils.normalize_date("20251025")
        assert result == "20251025"
    
    def test_normalize_date_with_datetime_object(self):
        """測試 datetime 物件"""
        dt = datetime(2025, 10, 25, 14, 30, 0)
        result = DateTimeUtils.normalize_date(dt)
        assert result == "20251025"
    
    def test_normalize_date_with_pandas_timestamp(self):
        """測試 pandas Timestamp"""
        ts = pd.Timestamp("2025-10-25")
        result = DateTimeUtils.normalize_date(ts)
        assert result == "20251025"
    
    def test_normalize_date_invalid_format(self):
        """測試無效格式"""
        with pytest.raises(ValueError):
            DateTimeUtils.normalize_date("invalid")
    
    def test_normalize_date_invalid_type(self):
        """測試無效類型"""
        with pytest.raises(TypeError):
            DateTimeUtils.normalize_date(12345)
    
    def test_normalize_datetime(self):
        """測試日期時間標準化"""
        result = DateTimeUtils.normalize_datetime("2025-10-25 14:30:00")
        assert result == "20251025143000"
    
    def test_normalize_datetime_date_only(self):
        """測試只有日期的標準化（應補上時間）"""
        result = DateTimeUtils.normalize_datetime("20251025")
        assert result == "20251025000000"
    
    def test_parse_db_date(self):
        """測試解析資料庫日期"""
        result = DateTimeUtils.parse_db_date("20251025")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 25
    
    def test_parse_db_datetime(self):
        """測試解析資料庫日期時間"""
        result = DateTimeUtils.parse_db_datetime("20251025143000")
        assert isinstance(result, datetime)
        assert result.hour == 14
        assert result.minute == 30
    
    def test_format_for_display_date_only(self):
        """測試顯示格式（僅日期）"""
        result = DateTimeUtils.format_for_display("20251025", include_time=False)
        assert result == "2025-10-25"
    
    def test_format_for_display_with_time(self):
        """測試顯示格式（包含時間）"""
        result = DateTimeUtils.format_for_display("20251025143000", include_time=True)
        assert result == "2025-10-25 14:30:00"
    
    def test_get_date_range(self):
        """測試日期範圍生成"""
        result = DateTimeUtils.get_date_range("2025-10-23", "2025-10-25")
        assert len(result) == 3
        assert result == ["20251023", "20251024", "20251025"]
    
    def test_is_valid_date_valid(self):
        """測試日期驗證（有效）"""
        assert DateTimeUtils.is_valid_date("2025-10-25") is True
        assert DateTimeUtils.is_valid_date("20251025") is True
    
    def test_is_valid_date_invalid(self):
        """測試日期驗證（無效）"""
        assert DateTimeUtils.is_valid_date("invalid") is False
        assert DateTimeUtils.is_valid_date("") is False
    
    def test_get_trading_days_ago(self):
        """測試取得過去日期"""
        result = DateTimeUtils.get_trading_days_ago(7, from_date="2025-10-25")
        assert result == "20251018"


class TestConvenienceFunctions:
    """便捷函式測試"""
    
    def test_normalize_date_shortcut(self):
        """測試快捷函式"""
        result = normalize_date("2025-10-25")
        assert result == "20251025"
    
    def test_format_for_display_shortcut(self):
        """測試快捷函式"""
        result = format_for_display("20251025")
        assert result == "2025-10-25"


# Pytest fixtures
@pytest.fixture
def sample_dates():
    """提供測試用的日期樣本"""
    return {
        'dash_format': '2025-10-25',
        'slash_format': '2025/10/25',
        'db_format': '20251025',
        'datetime_obj': datetime(2025, 10, 25),
    }


def test_all_formats_equivalent(sample_dates):
    """測試所有格式轉換後一致"""
    results = [
        DateTimeUtils.normalize_date(sample_dates['dash_format']),
        DateTimeUtils.normalize_date(sample_dates['slash_format']),
        DateTimeUtils.normalize_date(sample_dates['db_format']),
        DateTimeUtils.normalize_date(sample_dates['datetime_obj']),
    ]
    
    # 所有結果應該相同
    assert len(set(results)) == 1
    assert results[0] == "20251025"
