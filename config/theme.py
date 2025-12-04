"""
專業金融軟體主題配置

設計靈感: Bloomberg Terminal, TradingView, ThinkOrSwim, QuantConnect
採用深色主題設計，降低眼睛疲勞，凸顯數據可讀性
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorPalette:
    """核心色彩系統 - 基於 HSL 調和色盤"""
    
    # 主要背景色系
    BG_PRIMARY: str = "#0E1117"      # 最深背景
    BG_SECONDARY: str = "#1A1F2E"    # 卡片/側邊欄背景
    BG_TERTIARY: str = "#262D3D"     # hover 狀態背景
    BG_ELEVATED: str = "#2D3548"     # 彈出框背景
    
    # 邊框色
    BORDER_DEFAULT: str = "#30363D"
    BORDER_MUTED: str = "#21262D"
    BORDER_ACCENT: str = "#00D4AA"
    
    # 文字色系
    TEXT_PRIMARY: str = "#E6EDF3"    # 主要文字
    TEXT_SECONDARY: str = "#8B949E"  # 次要文字
    TEXT_MUTED: str = "#6E7681"      # 輔助文字
    TEXT_LINK: str = "#58A6FF"       # 連結
    
    # 語意色彩 - 金融專用
    PROFIT: str = "#00D4AA"          # 獲利綠 (青綠色調，較柔和)
    PROFIT_BG: str = "rgba(0, 212, 170, 0.12)"
    LOSS: str = "#FF6B6B"            # 虧損紅 (珊瑚紅，不刺眼)
    LOSS_BG: str = "rgba(255, 107, 107, 0.12)"
    
    NEUTRAL: str = "#8B949E"         # 中性灰
    WARNING: str = "#F0B429"         # 警告黃
    WARNING_BG: str = "rgba(240, 180, 41, 0.12)"
    INFO: str = "#58A6FF"            # 資訊藍
    INFO_BG: str = "rgba(88, 166, 255, 0.12)"
    
    # 圖表專用色
    CHART_BG: str = "#161B22"
    CHART_GRID: str = "#30363D"
    CHART_LINE_PRIMARY: str = "#00D4AA"
    CHART_LINE_SECONDARY: str = "#58A6FF"
    CHART_CANDLE_BULL: str = "#00D4AA"
    CHART_CANDLE_BEAR: str = "#FF6B6B"
    CHART_VOLUME: str = "#484F58"
    
    # 互動元素
    ACCENT_PRIMARY: str = "#00D4AA"
    ACCENT_SECONDARY: str = "#58A6FF"
    ACCENT_HOVER: str = "#00F5C4"


@dataclass(frozen=True)
class Typography:
    """字體系統 - 採用系統字體堆疊確保載入速度"""
    
    FONT_FAMILY_PRIMARY: str = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif"
    FONT_FAMILY_MONO: str = "'SF Mono', 'Fira Code', 'JetBrains Mono', monospace"
    
    # 字重
    FONT_WEIGHT_REGULAR: int = 400
    FONT_WEIGHT_MEDIUM: int = 500
    FONT_WEIGHT_SEMIBOLD: int = 600
    FONT_WEIGHT_BOLD: int = 700
    
    # 字號
    FONT_SIZE_XS: str = "0.75rem"    # 12px
    FONT_SIZE_SM: str = "0.875rem"   # 14px
    FONT_SIZE_BASE: str = "1rem"     # 16px
    FONT_SIZE_LG: str = "1.125rem"   # 18px
    FONT_SIZE_XL: str = "1.25rem"    # 20px
    FONT_SIZE_2XL: str = "1.5rem"    # 24px
    FONT_SIZE_3XL: str = "2rem"      # 32px
    FONT_SIZE_4XL: str = "2.5rem"    # 40px
    
    # 行高
    LINE_HEIGHT_TIGHT: float = 1.25
    LINE_HEIGHT_NORMAL: float = 1.5
    LINE_HEIGHT_RELAXED: float = 1.75


@dataclass(frozen=True)
class Spacing:
    """間距系統 - 基於 4px 網格"""
    
    SPACE_1: str = "0.25rem"   # 4px
    SPACE_2: str = "0.5rem"    # 8px
    SPACE_3: str = "0.75rem"   # 12px
    SPACE_4: str = "1rem"      # 16px
    SPACE_5: str = "1.25rem"   # 20px
    SPACE_6: str = "1.5rem"    # 24px
    SPACE_8: str = "2rem"      # 32px
    SPACE_10: str = "2.5rem"   # 40px
    SPACE_12: str = "3rem"     # 48px
    SPACE_16: str = "4rem"     # 64px


@dataclass(frozen=True)
class Effects:
    """效果與動畫"""
    
    # 圓角
    RADIUS_SM: str = "4px"
    RADIUS_MD: str = "8px"
    RADIUS_LG: str = "12px"
    RADIUS_XL: str = "16px"
    RADIUS_FULL: str = "9999px"
    
    # 陰影 - 深色主題較淡的陰影
    SHADOW_SM: str = "0 1px 2px rgba(0, 0, 0, 0.4)"
    SHADOW_MD: str = "0 4px 6px rgba(0, 0, 0, 0.4)"
    SHADOW_LG: str = "0 10px 15px rgba(0, 0, 0, 0.5)"
    SHADOW_XL: str = "0 20px 25px rgba(0, 0, 0, 0.6)"
    SHADOW_GLOW: str = "0 0 20px rgba(0, 212, 170, 0.3)"
    
    # 過渡
    TRANSITION_FAST: str = "150ms ease"
    TRANSITION_NORMAL: str = "200ms ease"
    TRANSITION_SLOW: str = "300ms ease"
    
    # 邊框
    BORDER_THIN: str = "1px solid"
    BORDER_MEDIUM: str = "2px solid"


@dataclass(frozen=True)
class ComponentStyles:
    """元件專用樣式"""
    
    # 卡片
    CARD_PADDING: str = "1.5rem"
    CARD_GAP: str = "1rem"
    
    # 指標數字 (Metric)
    METRIC_VALUE_SIZE: str = "2rem"
    METRIC_LABEL_SIZE: str = "0.875rem"
    METRIC_DELTA_SIZE: str = "0.75rem"
    
    # 按鈕
    BUTTON_HEIGHT_SM: str = "32px"
    BUTTON_HEIGHT_MD: str = "40px"
    BUTTON_HEIGHT_LG: str = "48px"


# 全域實例
COLORS = ColorPalette()
TYPOGRAPHY = Typography()
SPACING = Spacing()
EFFECTS = Effects()
COMPONENT_STYLES = ComponentStyles()


def get_chart_layout_config(title: str = "") -> dict:
    """取得 Plotly 圖表的深色主題配置"""
    return {
        'title': {
            'text': title,
            'font': {'color': COLORS.TEXT_PRIMARY, 'size': 16},
            'x': 0.5
        },
        'paper_bgcolor': COLORS.CHART_BG,
        'plot_bgcolor': COLORS.CHART_BG,
        'font': {
            'family': TYPOGRAPHY.FONT_FAMILY_PRIMARY,
            'color': COLORS.TEXT_SECONDARY,
            'size': 12
        },
        'margin': {'l': 60, 'r': 20, 't': 50, 'b': 40},
        'xaxis': {
            'showgrid': True,
            'gridcolor': COLORS.CHART_GRID,
            'gridwidth': 1,
            'showline': True,
            'linecolor': COLORS.BORDER_DEFAULT,
            'linewidth': 1,
            'tickfont': {'color': COLORS.TEXT_MUTED},
            'zeroline': False
        },
        'yaxis': {
            'showgrid': True,
            'gridcolor': COLORS.CHART_GRID,
            'gridwidth': 1,
            'showline': True,
            'linecolor': COLORS.BORDER_DEFAULT,
            'linewidth': 1,
            'tickfont': {'color': COLORS.TEXT_MUTED},
            'zeroline': True,
            'zerolinecolor': COLORS.BORDER_ACCENT,
            'zerolinewidth': 1
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': COLORS.BG_ELEVATED,
            'font': {'color': COLORS.TEXT_PRIMARY},
            'bordercolor': COLORS.BORDER_ACCENT
        },
        'legend': {
            'bgcolor': 'rgba(0,0,0,0)',
            'font': {'color': COLORS.TEXT_SECONDARY}
        }
    }
