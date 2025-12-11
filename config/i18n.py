"""
多語言支援系統 (Internationalization)

支援中文（繁體）和英文切換
"""

import streamlit as st
from typing import Dict


# 語言定義
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ===== 通用 =====
    'app_title': {
        'zh': 'AI 交易日誌',
        'en': 'AI Trading Journal'
    },
    'app_subtitle': {
        'zh': '智能交易日誌系統 | 由 AI 驅動的交易檢討與績效分析平台',
        'en': 'Smart Trading Journal | AI-Powered Trade Review & Performance Analysis'
    },
    
    # ===== 側邊欄選單 =====
    'menu_home': {
        'zh': '首頁',
        'en': 'Home'
    },
    'menu_review': {
        'zh': '交易檢討',
        'en': 'Trade Review'
    },
    'menu_strategy': {
        'zh': '策略分析',
        'en': 'Strategy'
    },
    'menu_report_card': {
        'zh': '績效報告',
        'en': 'Report Card'
    },
    'menu_strategy_lab': {
        'zh': '策略實驗室',
        'en': 'Strategy Lab'
    },
    'menu_options_strategy': {
        'zh': '選擇權策略',
        'en': 'Options Strategy'
    },
    'menu_portfolio_advisor': {
        'zh': '投資組合顧問',
        'en': 'Portfolio Advisor'
    },
    'menu_help': {
        'zh': '說明',
        'en': 'Help'
    },
    'menu_mistake_cards': {
        'zh': '錯誤卡片',
        'en': 'Mistake Cards'
    },
    'menu_history_ai': {
        'zh': '歷史 AI',
        'en': 'History AI'
    },
    
    # ===== KPI 指標 =====
    'kpi_total_pnl': {
        'zh': '總盈虧',
        'en': 'Total P&L'
    },
    'kpi_avg_win': {
        'zh': '平均獲利',
        'en': 'Avg Win'
    },
    'kpi_avg_loss': {
        'zh': '平均虧損',
        'en': 'Avg Loss'
    },
    'kpi_win_rate': {
        'zh': '勝率',
        'en': 'Win Rate'
    },
    'kpi_profit_factor': {
        'zh': '獲利因子',
        'en': 'Profit Factor'
    },
    'kpi_cash': {
        'zh': '現金',
        'en': 'Cash'
    },
    'kpi_total_trades': {
        'zh': '總交易數',
        'en': 'Total Trades'
    },
    
    # ===== 持倉相關 =====
    'portfolio_overview': {
        'zh': '持倉總覽',
        'en': 'Portfolio Overview'
    },
    'position_dynamics': {
        'zh': '標的動態',
        'en': 'Position Dynamics'
    },
    'sort_mode': {
        'zh': '排序模式',
        'en': 'Sort Mode'
    },
    'sort_recent': {
        'zh': '最近交易',
        'en': 'Recent Trades'
    },
    'sort_top_profit': {
        'zh': '獲利最高',
        'en': 'Top Profit'
    },
    'sort_top_loss': {
        'zh': '虧損最多',
        'en': 'Top Loss'
    },
    'sort_most_active': {
        'zh': '交易最頻繁',
        'en': 'Most Active'
    },
    'global_analysis': {
        'zh': '全局分析',
        'en': 'Global Analysis'
    },
    
    # ===== 策略相關 =====
    'strategy_covered_call': {
        'zh': '備兌看漲',
        'en': 'Covered Call'
    },
    'strategy_protective_put': {
        'zh': '保護性看跌',
        'en': 'Protective Put'
    },
    'strategy_collar': {
        'zh': '領口策略',
        'en': 'Collar'
    },
    'strategy_cash_secured_put': {
        'zh': '現金擔保看跌',
        'en': 'Cash Secured Put'
    },
    'strategy_bull_call_spread': {
        'zh': '牛市看漲價差',
        'en': 'Bull Call Spread'
    },
    'strategy_bear_put_spread': {
        'zh': '熊市看跌價差',
        'en': 'Bear Put Spread'
    },
    'strategy_iron_condor': {
        'zh': '鐵禿鷹',
        'en': 'Iron Condor'
    },
    'strategy_straddle': {
        'zh': '跨式',
        'en': 'Straddle'
    },
    'strategy_strangle': {
        'zh': '勒式',
        'en': 'Strangle'
    },
    'strategy_stock_only': {
        'zh': '純股票持倉',
        'en': 'Stock Only'
    },
    'strategy_options_only': {
        'zh': '純選擇權',
        'en': 'Options Only'
    },
    
    # ===== 圖表相關 =====
    'chart_cumulative_pnl': {
        'zh': '累計盈虧曲線',
        'en': 'Cumulative P&L'
    },
    'chart_equity_curve': {
        'zh': '資金曲線',
        'en': 'Equity Curve'
    },
    'chart_peak': {
        'zh': '峰值',
        'en': 'Peak'
    },
    
    # ===== 交易檢討 =====
    'review_title': {
        'zh': '交易檢討',
        'en': 'Trade Review'
    },
    'review_subtitle': {
        'zh': '與 AI 教練深度分析你的交易決策',
        'en': 'Deep analysis of your trading decisions with AI Coach'
    },
    'review_mode': {
        'zh': '檢討模式',
        'en': 'Review Mode'
    },
    'review_single': {
        'zh': '單一標的',
        'en': 'Single Symbol'
    },
    'review_all': {
        'zh': '全部標的總覽',
        'en': 'All Symbols Overview'
    },
    'review_date_range': {
        'zh': '日期範圍',
        'en': 'Date Range'
    },
    'review_load_data': {
        'zh': '載入數據',
        'en': 'Load Data'
    },
    'review_start_ai': {
        'zh': '開始 AI 綜合分析',
        'en': 'Start AI Analysis'
    },
    
    # ===== AI 教練 =====
    'ai_coach': {
        'zh': 'AI 教練對話',
        'en': 'AI Coach Chat'
    },
    'ai_ask': {
        'zh': '詢問 AI 教練...',
        'en': 'Ask AI Coach...'
    },
    'ai_clear': {
        'zh': '清除',
        'en': 'Clear'
    },
    'ai_history': {
        'zh': '歷史',
        'en': 'History'
    },
    'ai_greeting': {
        'zh': '有任何交易問題都可以問我！',
        'en': 'Feel free to ask me any trading questions!'
    },
    
    # ===== 按鈕與操作 =====
    'btn_sync': {
        'zh': '同步',
        'en': 'Sync'
    },
    'btn_details': {
        'zh': '詳情',
        'en': 'Details'
    },
    'btn_analyze': {
        'zh': '分析',
        'en': 'Analyze'
    },
    'btn_save': {
        'zh': '儲存',
        'en': 'Save'
    },
    'btn_cancel': {
        'zh': '取消',
        'en': 'Cancel'
    },
    
    # ===== 狀態訊息 =====
    'msg_no_data': {
        'zh': '尚無交易數據，請先同步 IBKR',
        'en': 'No trading data yet, please sync with IBKR first'
    },
    'msg_sync_success': {
        'zh': '同步完成',
        'en': 'Sync completed'
    },
    'msg_sync_failed': {
        'zh': '同步失敗',
        'en': 'Sync failed'
    },
    'msg_loading': {
        'zh': '載入中...',
        'en': 'Loading...'
    },
    'msg_analyzing': {
        'zh': 'AI 正在分析...',
        'en': 'AI is analyzing...'
    },
    
    # ===== 設定 =====
    'settings_language': {
        'zh': '語言',
        'en': 'Language'
    },
    'settings_theme': {
        'zh': '主題',
        'en': 'Theme'
    },
    'settings_dark': {
        'zh': '深色',
        'en': 'Dark'
    },
    'settings_light': {
        'zh': '淺色',
        'en': 'Light'
    },
    
    # ===== 報告相關 =====
    'report_period': {
        'zh': '分析期間',
        'en': 'Analysis Period'
    },
    'report_winners': {
        'zh': '獲利標的',
        'en': 'Winners'
    },
    'report_losers': {
        'zh': '虧損標的',
        'en': 'Losers'
    },
    'report_trades': {
        'zh': '交易次數',
        'en': 'Trades'
    },
}


def get_language() -> str:
    """取得當前語言設定"""
    return st.session_state.get('app_language', 'zh')


def set_language(lang: str):
    """設定語言"""
    if lang in ['zh', 'en']:
        st.session_state['app_language'] = lang


def t(key: str) -> str:
    """
    翻譯函數
    
    Args:
        key: 翻譯鍵值
        
    Returns:
        翻譯後的文字
    """
    lang = get_language()
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('zh', key))
    return key


def render_language_selector():
    """渲染語言選擇器"""
    current_lang = get_language()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🇹🇼 中文", 
                     key="lang_zh", 
                     use_container_width=True,
                     type="primary" if current_lang == 'zh' else "secondary"):
            set_language('zh')
            st.rerun()
    with col2:
        if st.button("🇺🇸 English", 
                     key="lang_en", 
                     use_container_width=True,
                     type="primary" if current_lang == 'en' else "secondary"):
            set_language('en')
            st.rerun()
