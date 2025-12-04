"""
專業金融軟體 UI 樣式模組

提供 Streamlit 自定義 CSS 和可重用的 UI 元件
"""

import streamlit as st
from config.theme import COLORS, TYPOGRAPHY, SPACING, EFFECTS


def inject_custom_css():
    """
    注入專業金融軟體風格的自定義 CSS
    
    應在每個頁面的開頭呼叫此函數
    """
    st.markdown(f"""
    <style>
    /* ============================================
       全域樣式重置與基礎設定
       ============================================ */
    
    /* 導入 Inter 字體 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* 全域字體設定 */
    html, body, [class*="css"] {{
        font-family: {TYPOGRAPHY.FONT_FAMILY_PRIMARY};
    }}
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* 主要容器背景 */
    .stApp {{
        background: linear-gradient(180deg, {COLORS.BG_PRIMARY} 0%, #0A0D12 100%);
    }}
    
    /* ============================================
       側邊欄樣式
       ============================================ */
    
    [data-testid="stSidebar"] {{
        background: {COLORS.BG_SECONDARY};
        border-right: 1px solid {COLORS.BORDER_MUTED};
    }}
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
        color: {COLORS.TEXT_PRIMARY};
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_SEMIBOLD};
    }}
    
    /* ============================================
       卡片與容器樣式
       ============================================ */
    
    /* Streamlit 內建容器邊框 */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stVerticalBlockBorderWrapper"]) {{
        background: {COLORS.BG_SECONDARY};
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_4};
        transition: all {EFFECTS.TRANSITION_NORMAL};
    }}
    
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stVerticalBlockBorderWrapper"]):hover {{
        border-color: {COLORS.BORDER_ACCENT};
        box-shadow: {EFFECTS.SHADOW_GLOW};
    }}
    
    /* Expander 樣式 */
    .streamlit-expanderHeader {{
        background: {COLORS.BG_TERTIARY} !important;
        border-radius: {EFFECTS.RADIUS_MD};
        color: {COLORS.TEXT_PRIMARY} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_MEDIUM};
    }}
    
    .streamlit-expanderContent {{
        background: {COLORS.BG_SECONDARY};
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-top: none;
        border-radius: 0 0 {EFFECTS.RADIUS_MD} {EFFECTS.RADIUS_MD};
    }}
    
    /* ============================================
       Metric (指標數字) 樣式 - 金融數據展示核心
       ============================================ */
    
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, {COLORS.BG_SECONDARY} 0%, {COLORS.BG_TERTIARY} 100%);
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_4};
        transition: transform {EFFECTS.TRANSITION_NORMAL}, box-shadow {EFFECTS.TRANSITION_NORMAL};
    }}
    
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: {EFFECTS.SHADOW_MD};
        border-color: {COLORS.BORDER_ACCENT};
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {COLORS.TEXT_SECONDARY} !important;
        font-size: {TYPOGRAPHY.FONT_SIZE_SM} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_MEDIUM} !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    [data-testid="stMetricValue"] {{
        color: {COLORS.TEXT_PRIMARY} !important;
        font-size: {TYPOGRAPHY.FONT_SIZE_2XL} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_BOLD} !important;
        font-family: {TYPOGRAPHY.FONT_FAMILY_MONO};
    }}
    
    [data-testid="stMetricDelta"] {{
        font-size: {TYPOGRAPHY.FONT_SIZE_SM} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_MEDIUM} !important;
    }}
    
    /* 正值 Delta */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {{
        color: {COLORS.PROFIT} !important;
    }}
    [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Up"]) {{
        color: {COLORS.PROFIT} !important;
    }}
    
    /* 負值 Delta */
    [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {{
        color: {COLORS.LOSS} !important;
    }}
    [data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) {{
        color: {COLORS.LOSS} !important;
    }}
    
    /* ============================================
       按鈕樣式
       ============================================ */
    
    /* 主要按鈕 */
    .stButton > button[kind="primary"],
    .stButton > button[data-baseweb="button"][kind="primary"] {{
        background: linear-gradient(135deg, {COLORS.ACCENT_PRIMARY} 0%, #00B894 100%) !important;
        border: none !important;
        color: {COLORS.BG_PRIMARY} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_SEMIBOLD} !important;
        border-radius: {EFFECTS.RADIUS_MD} !important;
        padding: {SPACING.SPACE_2} {SPACING.SPACE_4} !important;
        transition: all {EFFECTS.TRANSITION_FAST} !important;
        box-shadow: 0 2px 8px rgba(0, 212, 170, 0.3) !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 212, 170, 0.4) !important;
    }}
    
    /* 次要按鈕 */
    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {{
        background: {COLORS.BG_TERTIARY} !important;
        border: 1px solid {COLORS.BORDER_DEFAULT} !important;
        color: {COLORS.TEXT_PRIMARY} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_MEDIUM} !important;
        border-radius: {EFFECTS.RADIUS_MD} !important;
        transition: all {EFFECTS.TRANSITION_FAST} !important;
    }}
    
    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {{
        background: {COLORS.BG_ELEVATED} !important;
        border-color: {COLORS.ACCENT_PRIMARY} !important;
        color: {COLORS.ACCENT_PRIMARY} !important;
    }}
    
    /* ============================================
       資料表格樣式
       ============================================ */
    
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: {EFFECTS.RADIUS_LG};
        overflow: hidden;
    }}
    
    [data-testid="stDataFrame"] [data-testid="glideDataEditor"] {{
        background: {COLORS.BG_SECONDARY} !important;
    }}
    
    /* 表頭 */
    [data-testid="stDataFrame"] .dvn-header {{
        background: {COLORS.BG_TERTIARY} !important;
        color: {COLORS.TEXT_PRIMARY} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_SEMIBOLD} !important;
    }}
    
    /* ============================================
       選擇框與輸入框樣式
       ============================================ */
    
    [data-baseweb="select"],
    [data-baseweb="input"] {{
        background: {COLORS.BG_TERTIARY} !important;
        border-color: {COLORS.BORDER_DEFAULT} !important;
        border-radius: {EFFECTS.RADIUS_MD} !important;
    }}
    
    [data-baseweb="select"]:focus-within,
    [data-baseweb="input"]:focus-within {{
        border-color: {COLORS.ACCENT_PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.2) !important;
    }}
    
    /* ============================================
       標籤頁 (Tabs) 樣式
       ============================================ */
    
    .stTabs [data-baseweb="tab-list"] {{
        background: {COLORS.BG_SECONDARY};
        border-radius: {EFFECTS.RADIUS_MD};
        padding: {SPACING.SPACE_1};
        gap: {SPACING.SPACE_1};
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        color: {COLORS.TEXT_SECONDARY};
        border-radius: {EFFECTS.RADIUS_SM};
        padding: {SPACING.SPACE_2} {SPACING.SPACE_4};
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_MEDIUM};
        transition: all {EFFECTS.TRANSITION_FAST};
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        background: {COLORS.BG_TERTIARY};
        color: {COLORS.TEXT_PRIMARY};
    }}
    
    .stTabs [aria-selected="true"] {{
        background: {COLORS.ACCENT_PRIMARY} !important;
        color: {COLORS.BG_PRIMARY} !important;
    }}
    
    /* ============================================
       警告 / 成功 / 錯誤訊息樣式
       ============================================ */
    
    .stAlert {{
        border-radius: {EFFECTS.RADIUS_MD};
        border: 1px solid;
    }}
    
    [data-testid="stAlert"][data-baseweb="notification"][kind="success"] {{
        background: {COLORS.PROFIT_BG} !important;
        border-color: {COLORS.PROFIT} !important;
    }}
    
    [data-testid="stAlert"][data-baseweb="notification"][kind="error"] {{
        background: {COLORS.LOSS_BG} !important;
        border-color: {COLORS.LOSS} !important;
    }}
    
    [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {{
        background: {COLORS.WARNING_BG} !important;
        border-color: {COLORS.WARNING} !important;
    }}
    
    [data-testid="stAlert"][data-baseweb="notification"][kind="info"] {{
        background: {COLORS.INFO_BG} !important;
        border-color: {COLORS.INFO} !important;
    }}
    
    /* ============================================
       聊天介面樣式 (AI Coach)
       ============================================ */
    
    [data-testid="stChatMessage"] {{
        background: {COLORS.BG_SECONDARY} !important;
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_4};
        margin-bottom: {SPACING.SPACE_2};
    }}
    
    [data-testid="stChatMessage"][data-testid="user-message"] {{
        background: linear-gradient(135deg, {COLORS.BG_TERTIARY} 0%, {COLORS.BG_ELEVATED} 100%) !important;
        border-left: 3px solid {COLORS.ACCENT_SECONDARY};
    }}
    
    [data-testid="stChatMessage"][data-testid="assistant-message"] {{
        border-left: 3px solid {COLORS.ACCENT_PRIMARY};
    }}
    
    /* 聊天輸入框 */
    [data-testid="stChatInput"] {{
        background: {COLORS.BG_SECONDARY} !important;
        border: 1px solid {COLORS.BORDER_DEFAULT} !important;
        border-radius: {EFFECTS.RADIUS_LG} !important;
    }}
    
    [data-testid="stChatInput"]:focus-within {{
        border-color: {COLORS.ACCENT_PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.2) !important;
    }}
    
    /* ============================================
       進度條樣式
       ============================================ */
    
    [data-testid="stProgress"] > div {{
        background: {COLORS.BG_TERTIARY} !important;
        border-radius: {EFFECTS.RADIUS_FULL};
    }}
    
    [data-testid="stProgress"] > div > div {{
        background: linear-gradient(90deg, {COLORS.ACCENT_PRIMARY} 0%, {COLORS.ACCENT_SECONDARY} 100%) !important;
        border-radius: {EFFECTS.RADIUS_FULL};
    }}
    
    /* ============================================
       分隔線樣式
       ============================================ */
    
    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, {COLORS.BORDER_DEFAULT} 50%, transparent 100%);
        margin: {SPACING.SPACE_6} 0;
    }}
    
    /* ============================================
       標題樣式
       ============================================ */
    
    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS.TEXT_PRIMARY} !important;
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_SEMIBOLD} !important;
    }}
    
    h1 {{
        font-size: {TYPOGRAPHY.FONT_SIZE_3XL} !important;
        background: linear-gradient(135deg, {COLORS.TEXT_PRIMARY} 0%, {COLORS.ACCENT_PRIMARY} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    
    h2 {{
        font-size: {TYPOGRAPHY.FONT_SIZE_2XL} !important;
        border-bottom: 2px solid {COLORS.BORDER_MUTED};
        padding-bottom: {SPACING.SPACE_2};
    }}
    
    h3 {{
        font-size: {TYPOGRAPHY.FONT_SIZE_XL} !important;
    }}
    
    /* ============================================
       自定義元件類別
       ============================================ */
    
    /* 獲利卡片 */
    .profit-card {{
        background: linear-gradient(135deg, {COLORS.PROFIT_BG} 0%, rgba(0, 212, 170, 0.05) 100%);
        border: 1px solid {COLORS.PROFIT};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_4};
    }}
    
    /* 虧損卡片 */
    .loss-card {{
        background: linear-gradient(135deg, {COLORS.LOSS_BG} 0%, rgba(255, 107, 107, 0.05) 100%);
        border: 1px solid {COLORS.LOSS};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_4};
    }}
    
    /* 金額數字樣式 */
    .money-value {{
        font-family: {TYPOGRAPHY.FONT_FAMILY_MONO};
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_BOLD};
        font-size: {TYPOGRAPHY.FONT_SIZE_2XL};
    }}
    
    .money-value.profit {{
        color: {COLORS.PROFIT};
    }}
    
    .money-value.loss {{
        color: {COLORS.LOSS};
    }}
    
    /* 儀表板統計卡片 */
    .stat-card {{
        background: {COLORS.BG_SECONDARY};
        border: 1px solid {COLORS.BORDER_DEFAULT};
        border-radius: {EFFECTS.RADIUS_LG};
        padding: {SPACING.SPACE_5};
        text-align: center;
        transition: all {EFFECTS.TRANSITION_NORMAL};
    }}
    
    .stat-card:hover {{
        border-color: {COLORS.ACCENT_PRIMARY};
        box-shadow: {EFFECTS.SHADOW_GLOW};
        transform: translateY(-2px);
    }}
    
    .stat-card .stat-value {{
        font-size: {TYPOGRAPHY.FONT_SIZE_3XL};
        font-weight: {TYPOGRAPHY.FONT_WEIGHT_BOLD};
        font-family: {TYPOGRAPHY.FONT_FAMILY_MONO};
        color: {COLORS.TEXT_PRIMARY};
    }}
    
    .stat-card .stat-label {{
        font-size: {TYPOGRAPHY.FONT_SIZE_SM};
        color: {COLORS.TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: {SPACING.SPACE_2};
    }}
    
    /* 脈動動畫效果 */
    @keyframes pulse-glow {{
        0%, 100% {{ box-shadow: 0 0 5px rgba(0, 212, 170, 0.3); }}
        50% {{ box-shadow: 0 0 20px rgba(0, 212, 170, 0.6); }}
    }}
    
    .pulse-glow {{
        animation: pulse-glow 2s ease-in-out infinite;
    }}
    
    /* 滾動條樣式 */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {COLORS.BG_SECONDARY};
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: {COLORS.BG_ELEVATED};
        border-radius: {EFFECTS.RADIUS_FULL};
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS.ACCENT_PRIMARY};
    }}
    
    </style>
    """, unsafe_allow_html=True)


def render_stat_card(label: str, value: str, delta: str = None, delta_type: str = "neutral") -> None:
    """
    渲染專業統計卡片
    
    Args:
        label: 指標名稱
        value: 指標數值
        delta: 變化值 (可選)
        delta_type: 變化類型 ('profit', 'loss', 'neutral')
    """
    delta_color = {
        "profit": COLORS.PROFIT,
        "loss": COLORS.LOSS,
        "neutral": COLORS.TEXT_MUTED
    }.get(delta_type, COLORS.TEXT_MUTED)
    
    delta_html = ""
    if delta:
        delta_html = f'<div style="color: {delta_color}; font-size: 0.875rem; margin-top: 0.5rem;">{delta}</div>'
    
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_pnl_value(value: float, prefix: str = "$", show_sign: bool = True) -> str:
    """
    渲染盈虧金額 (帶顏色)
    
    Args:
        value: 金額數值
        prefix: 前綴符號
        show_sign: 是否顯示正負號
    
    Returns:
        HTML 格式的金額字串
    """
    color = COLORS.PROFIT if value >= 0 else COLORS.LOSS
    sign = "+" if value >= 0 and show_sign else ""
    formatted_value = f"{prefix}{sign}{value:,.2f}"
    
    return f'<span class="money-value" style="color: {color};">{formatted_value}</span>'


def render_header_with_subtitle(title: str, subtitle: str) -> None:
    """
    渲染帶副標題的標題區塊
    
    Args:
        title: 主標題
        subtitle: 副標題描述
    """
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h1 style="margin-bottom: 0.5rem;">{title}</h1>
        <p style="color: {COLORS.TEXT_SECONDARY}; font-size: 1.125rem; margin: 0;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_trading_signal(signal_type: str, price: float, label: str = "") -> None:
    """
    渲染交易信號標籤
    
    Args:
        signal_type: 信號類型 ('buy', 'sell', 'hold', 'stop_loss', 'take_profit')
        price: 價格
        label: 額外標籤
    """
    configs = {
        "buy": {"bg": COLORS.PROFIT_BG, "border": COLORS.PROFIT, "icon": "📈", "text": "買入"},
        "sell": {"bg": COLORS.LOSS_BG, "border": COLORS.LOSS, "icon": "📉", "text": "賣出"},
        "hold": {"bg": COLORS.INFO_BG, "border": COLORS.INFO, "icon": "⏸️", "text": "持有"},
        "stop_loss": {"bg": COLORS.LOSS_BG, "border": COLORS.LOSS, "icon": "🛑", "text": "停損"},
        "take_profit": {"bg": COLORS.PROFIT_BG, "border": COLORS.PROFIT, "icon": "🎯", "text": "停利"}
    }
    
    config = configs.get(signal_type, configs["hold"])
    
    st.markdown(f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: {config['bg']};
        border: 1px solid {config['border']};
        border-radius: {EFFECTS.RADIUS_MD};
        padding: 0.5rem 1rem;
        margin: 0.25rem;
    ">
        <span>{config['icon']}</span>
        <span style="font-weight: 600;">{config['text']}</span>
        <span style="font-family: monospace; font-weight: 700;">${price:,.2f}</span>
        {f'<span style="color: {COLORS.TEXT_MUTED}; font-size: 0.875rem;">({label})</span>' if label else ''}
    </div>
    """, unsafe_allow_html=True)
