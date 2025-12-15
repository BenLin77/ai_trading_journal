/**
 * 多語言支援系統
 */

export const translations = {
  // App
  app_title: { zh: 'AI 交易日誌', en: 'AI Trading Journal' },
  app_subtitle: { zh: '智能交易日誌系統', en: 'Smart Trading Journal System' },

  // Navigation
  nav_dashboard: { zh: '儀表板', en: 'Dashboard' },
  nav_review: { zh: '交易檢討', en: 'Trade Review' },
  nav_journal: { zh: '交易日誌', en: 'Journal' },
  nav_strategy: { zh: '策略模擬', en: 'Strategy' },
  nav_report: { zh: '績效成績單', en: 'Report Card' },
  nav_lab: { zh: '策略回測', en: 'Strategy Lab' },
  nav_options: { zh: '選擇權顧問', en: 'Options Strategy' },
  nav_ai: { zh: 'Portfolio AI', en: 'Portfolio AI' },
  nav_mistakes: { zh: '錯誤卡片', en: 'Mistake Cards' },
  nav_settings: { zh: '設定', en: 'Settings' },

  // KPI
  kpi_total_pnl: { zh: '總盈虧', en: 'Total P&L' },
  kpi_avg_win: { zh: '平均獲利', en: 'Avg Win' },
  kpi_avg_loss: { zh: '平均虧損', en: 'Avg Loss' },
  kpi_win_rate: { zh: '勝率', en: 'Win Rate' },
  kpi_profit_factor: { zh: '獲利因子', en: 'Profit Factor' },
  kpi_cash: { zh: '現金', en: 'Cash' },
  kpi_trades: { zh: '交易筆數', en: 'Trades' },
  kpi_symbols: { zh: '標的數量', en: 'Symbols' },

  // Portfolio
  portfolio_overview: { zh: '持倉總覽', en: 'Portfolio Overview' },
  portfolio_positions: { zh: '持倉', en: 'Positions' },
  portfolio_market_value: { zh: '市值', en: 'Market Value' },
  portfolio_unrealized: { zh: '未實現損益', en: 'Unrealized P&L' },
  portfolio_realized: { zh: '已實現損益', en: 'Realized P&L' },
  portfolio_current_price: { zh: '現價', en: 'Current Price' },
  portfolio_avg_cost: { zh: '平均成本', en: 'Avg Cost' },
  portfolio_quantity: { zh: '數量', en: 'Quantity' },
  portfolio_strategy: { zh: '策略', en: 'Strategy' },

  // Charts
  chart_equity_curve: { zh: '累計盈虧曲線', en: 'Equity Curve' },
  chart_distribution: { zh: '持倉分布', en: 'Position Distribution' },

  // Actions
  action_sync: { zh: '同步', en: 'Sync' },
  action_refresh: { zh: '重新整理', en: 'Refresh' },
  action_analyze: { zh: '分析', en: 'Analyze' },
  action_details: { zh: '詳情', en: 'Details' },
  action_recalculate: { zh: '重算盈虧', en: 'Recalculate P&L' },
  action_clear: { zh: '清空資料庫', en: 'Clear Database' },
  action_save: { zh: '儲存', en: 'Save' },
  action_cancel: { zh: '取消', en: 'Cancel' },
  action_confirm: { zh: '確認', en: 'Confirm' },

  // Settings
  settings_language: { zh: '語言', en: 'Language' },
  settings_theme: { zh: '主題', en: 'Theme' },
  settings_dark: { zh: '深色', en: 'Dark' },
  settings_light: { zh: '淺色', en: 'Light' },
  settings_maintenance: { zh: '系統設定', en: 'Settings' },

  // Status
  status_syncing: { zh: '同步中...', en: 'Syncing...' },
  status_loading: { zh: '載入中...', en: 'Loading...' },
  status_analyzing: { zh: '分析中...', en: 'Analyzing...' },
  status_success: { zh: '成功', en: 'Success' },
  status_error: { zh: '錯誤', en: 'Error' },
  status_no_data: { zh: '無資料', en: 'No Data' },
  status_no_position: { zh: '無持倉', en: 'No Position' },
  status_configured: { zh: '已設定', en: 'Configured' },
  status_not_configured: { zh: '未設定', en: 'Not Configured' },

  // AI Chat
  ai_chat_title: { zh: 'AI 助手', en: 'AI Assistant' },
  ai_chat_placeholder: { zh: '輸入問題...', en: 'Type your question...' },
  ai_chat_send: { zh: '發送', en: 'Send' },
  ai_thinking: { zh: '思考中...', en: 'Thinking...' },

  // Strategy
  strategy_simulation: { zh: '策略模擬', en: 'Strategy Simulation' },
  strategy_add_position: { zh: '加碼進場', en: 'Add Position' },
  strategy_take_profit: { zh: '獲利了結', en: 'Take Profit' },
  strategy_hedge: { zh: '對沖風險', en: 'Hedge' },
  strategy_spread: { zh: '價差交易', en: 'Spread' },

  // Options
  options_bullish: { zh: '看漲', en: 'Bullish' },
  options_bearish: { zh: '看跌', en: 'Bearish' },
  options_neutral: { zh: '中性', en: 'Neutral' },
  options_volatile: { zh: '高波動', en: 'Volatile' },

  // Risk
  risk_low: { zh: '低', en: 'Low' },
  risk_medium: { zh: '中等', en: 'Medium' },
  risk_high: { zh: '高', en: 'High' },

  // Time
  time_today: { zh: '今天', en: 'Today' },
  time_yesterday: { zh: '昨天', en: 'Yesterday' },

  // Misc
  misc_account_overview: { zh: '帳戶總覽', en: 'Account Overview' },
  misc_navigation: { zh: '功能導航', en: 'Navigation' },
  misc_tip: { zh: '提示: 資料來自 IBKR 同步', en: 'Tip: Data synced from IBKR' },
  misc_warning: { zh: '警告', en: 'Warning' },
  misc_lesson: { zh: '教訓', en: 'Lesson' },
} as const;

export type TranslationKey = keyof typeof translations;
export type Language = 'zh' | 'en';

export function t(key: TranslationKey, language: Language): string {
  return translations[key]?.[language] || key;
}

