"""
錯誤處理模組

提供裝飾器和工具函數來統一處理錯誤
"""

import logging
import functools
from typing import Callable, Any, Optional
import streamlit as st


def safe_execute(
    default_return: Any = None,
    show_error_to_user: bool = True,
    error_message: Optional[str] = None
):
    """
    裝飾器：捕獲並處理函數錯誤

    Args:
        default_return: 發生錯誤時的預設回傳值
        show_error_to_user: 是否在 Streamlit UI 顯示錯誤
        error_message: 自訂錯誤訊息

    Examples:
        @safe_execute(default_return=[], show_error_to_user=True)
        def get_trades(self):
            # ... 可能拋出異常的代碼
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 記錄詳細錯誤
                logging.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True,
                    extra={
                        'function': func.__name__,
                        'args': str(args)[:200],  # 限制長度避免日誌過大
                        'kwargs': str(kwargs)[:200]
                    }
                )

                # 顯示錯誤給用戶
                if show_error_to_user:
                    try:
                        msg = error_message or f"❌ 操作失敗：{str(e)}"
                        st.error(msg)
                    except:
                        # 如果不在 Streamlit 環境，忽略
                        pass

                return default_return

        return wrapper
    return decorator


def safe_database_operation(func: Callable) -> Callable:
    """
    資料庫操作專用錯誤處理

    自動處理資料庫連接錯誤、SQL 語法錯誤等
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            logging.error(
                f"Database error in {func.__name__}: {error_type} - {str(e)}",
                exc_info=True
            )

            # 根據錯誤類型提供友善訊息
            if 'locked' in str(e).lower():
                user_msg = "資料庫正忙，請稍後再試"
            elif 'no such table' in str(e).lower():
                user_msg = "資料庫表格不存在，請重新初始化"
            elif 'syntax error' in str(e).lower():
                user_msg = "資料查詢錯誤，請聯繫技術支援"
            else:
                user_msg = f"資料庫操作失敗：{str(e)}"

            try:
                st.error(f"❌ {user_msg}")
            except:
                pass

            return None

    return wrapper


class ErrorCollector:
    """
    錯誤收集器

    用於收集批次操作中的錯誤，最後統一顯示
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, message: str, details: Optional[str] = None):
        """添加錯誤"""
        self.errors.append({
            'message': message,
            'details': details
        })
        logging.error(f"{message} | Details: {details}")

    def add_warning(self, message: str, details: Optional[str] = None):
        """添加警告"""
        self.warnings.append({
            'message': message,
            'details': details
        })
        logging.warning(f"{message} | Details: {details}")

    def has_errors(self) -> bool:
        """是否有錯誤"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def display_summary(self):
        """在 Streamlit 顯示錯誤摘要"""
        if self.has_errors():
            with st.expander(f"❌ 發現 {len(self.errors)} 個錯誤", expanded=True):
                for i, error in enumerate(self.errors, 1):
                    st.error(f"{i}. {error['message']}")
                    if error['details']:
                        st.caption(f"詳情: {error['details']}")

        if self.has_warnings():
            with st.expander(f"⚠️ 發現 {len(self.warnings)} 個警告"):
                for i, warning in enumerate(self.warnings, 1):
                    st.warning(f"{i}. {warning['message']}")
                    if warning['details']:
                        st.caption(f"詳情: {warning['details']}")

    def clear(self):
        """清空錯誤"""
        self.errors.clear()
        self.warnings.clear()
