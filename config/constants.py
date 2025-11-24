"""
全域配置常數

集中管理所有魔法數字和配置參數
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChartConfig:
    """圖表配置"""
    DEFAULT_HEIGHT: int = 450
    PROFIT_COLOR: str = "#3B82F6"  # 藍色
    LOSS_COLOR: str = "#EF4444"     # 紅色
    NEUTRAL_COLOR: str = "#6B7280"  # 灰色
    SUCCESS_COLOR: str = "#10B981"  # 綠色
    WARNING_COLOR: str = "#F59E0B"  # 橙色
    
    GRID_COLOR: str = "#E5E7EB"
    BACKGROUND_COLOR: str = "#F9FAFB"
    ZERO_LINE_COLOR: str = "#9CA3AF"
    
    LINE_WIDTH: int = 3
    MARKER_SIZE: int = 12


@dataclass(frozen=True)
class TradingConfig:
    """交易分析配置"""
    FOMO_THRESHOLD: float = 0.02       # 追高閾值 2%
    PANIC_THRESHOLD: float = 0.02      # 殺低閾值 2%
    POOR_TIMING_THRESHOLD: float = 0.05 # 接刀閾值 5%
    
    MAX_DAILY_TRADES: int = 10         # 每日交易上限警告
    HIGH_FREQUENCY_THRESHOLD: int = 5   # 高頻交易警告
    
    MIN_HOLD_TIME_MINUTES: int = 5     # 最小持倉時間（分鐘）
    
    # 勝率計算
    MIN_TRADES_FOR_STATS: int = 10     # 需要至少 10 筆交易才有統計意義


@dataclass(frozen=True)
class DatabaseConfig:
    """資料庫配置"""
    DB_PATH: str = "trading_journal.db"
    DATE_FORMAT: str = "%Y%m%d"
    DATETIME_FORMAT: str = "%Y%m%d%H%M%S"
    
    # 資料庫快取 TTL（秒）
    CACHE_TTL: int = 300  # 5 分鐘


@dataclass(frozen=True)
class UIConfig:
    """UI 配置"""
    PAGE_TITLE: str = "AI 交易日誌"
    PAGE_ICON: str = "📊"
    LAYOUT: str = "wide"
    
    # 資料表顯示
    DEFAULT_PAGE_SIZE: int = 20
    MAX_DISPLAY_ROWS: int = 1000
    
    # 日期範圍預設值（天）
    DEFAULT_DATE_RANGE_DAYS: int = 30


@dataclass(frozen=True)
class AIConfig:
    """AI 配置"""
    MODEL_NAME: str = "gemini-1.5-flash"
    MAX_TOKENS: int = 8000
    TEMPERATURE: float = 0.7
    
    # 對話記憶長度
    MEMORY_LIMIT: int = 50  # 最多記住 50 條對話


@dataclass(frozen=True)
class ValidationRules:
    """驗證規則"""
    MIN_PRICE: float = 0.01
    MAX_PRICE: float = 1000000
    
    MIN_QUANTITY: float = 0.001
    MAX_QUANTITY: float = 1000000
    
    MAX_COMMISSION_RATE: float = 0.1  # 10% (異常高的手續費)


# 全域實例
CHART_CONFIG = ChartConfig()
TRADING_CONFIG = TradingConfig()
DATABASE_CONFIG = DatabaseConfig()
UI_CONFIG = UIConfig()
AI_CONFIG = AIConfig()
VALIDATION_RULES = ValidationRules()
