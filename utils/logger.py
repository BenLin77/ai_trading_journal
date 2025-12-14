"""
統一日誌配置模組

提供整個應用程式的標準化日誌設定
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    建立標準化的 Logger
    
    Args:
        name: Logger 名稱 (通常使用 __name__)
        level: 日誌等級
        
    Returns:
        配置好的 Logger 實例
    """
    logger = logging.getLogger(name)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# 預設 Logger
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    取得 Logger 實例
    
    Args:
        name: Logger 名稱，若 None 則使用 root logger
        
    Returns:
        Logger 實例
    """
    return setup_logger(name or 'ai_trading_journal')
