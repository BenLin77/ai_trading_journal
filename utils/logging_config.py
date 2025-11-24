"""
統一 Logging 配置

此模組負責：
1. 設定全域 logging 配置
2. 提供不同等級的 logger
3. 記錄到檔案和控制台
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "trading_journal.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
):
    """
    設定全域 logging 配置
    
    Args:
        log_level: 日誌等級 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日誌檔案路徑
        max_bytes: 單個日誌檔案最大大小
        backup_count: 保留的日誌檔案數量
    """
    # 確保日誌目錄存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 設定日誌格式
    log_format = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 清除現有 handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 設定根 logger 等級
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 檔案 Handler (使用 RotatingFileHandler)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 檔案記錄所有等級
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # 控制台 Handler (僅記錄 WARNING 以上)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 記錄初始化訊息
    logging.info("=" * 80)
    logging.info(f"Logging initialized at {datetime.now()}")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log file: {log_file}")
    logging.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    取得指定名稱的 logger
    
    Args:
        name: logger 名稱（通常使用 __name__）
        
    Returns:
        Logger 物件
        
    Examples:
        logger = get_logger(__name__)
        logger.info("交易載入成功")
    """
    return logging.getLogger(name)


# 便捷函式
def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None):
    """記錄函式調用"""
    logger = logging.getLogger("function_calls")
    logger.debug(f"Calling {func_name}(args={args}, kwargs={kwargs})")


def log_database_query(query: str, params: list = None):
    """記錄資料庫查詢"""
    logger = logging.getLogger("database")
    logger.debug(f"SQL: {query}")
    if params:
        logger.debug(f"Params: {params}")


def log_api_request(url: str, method: str = "GET", status_code: int = None):
    """記錄 API 請求"""
    logger = logging.getLogger("api")
    logger.info(f"{method} {url} - Status: {status_code}")


def log_performance_metric(metric_name: str, value: float, unit: str = ""):
    """記錄效能指標"""
    logger = logging.getLogger("performance")
    logger.info(f"METRIC: {metric_name} = {value:.4f} {unit}")
