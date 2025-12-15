/**
 * API Client - 與 FastAPI 後端通訊
 */

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Trade {
  id: number;
  symbol: string;
  datetime: string;
  action: string;
  quantity: number;
  price: number;
  commission: number;
  realized_pnl: number;
  notes?: string;
}

export interface Statistics {
  total_trades: number;
  total_pnl: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  best_trade: number;
  worst_trade: number;
}

export interface OptionLeg {
  symbol: string;
  option_type: 'call' | 'put';
  strike: number;
  expiry: string;
  quantity: number;
  action: 'buy' | 'sell';
}

export interface Position {
  symbol: string;
  underlying: string;
  quantity: number;
  avg_cost: number;
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  realized_pnl: number;
  strategy?: string;
  strategy_description?: string;
  options: OptionLeg[];
  // Greek 風險指標
  risk_level?: string;
  delta?: number;
  gamma?: number;
  vega?: number;
  theta?: number;
}

export interface PortfolioOverview {
  positions: Position[];
  total_market_value: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  cash_balance: number;
}

export interface CashBalance {
  total_cash: number;
  currency: string;
  ending_cash: number;
  ending_settled_cash: number;
}

export interface EquityCurvePoint {
  datetime: string;
  cumulative_pnl: number;
  symbol: string;
}

export interface AIResponse {
  response: string;
  session_id: string;
}

// K 線圖數據
export interface OHLCData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartTrade {
  date: string;
  datetime: string;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  realized_pnl: number;
  instrument_type: string;
  is_option: boolean;
  strike?: number;
  expiry?: string;
  option_type?: string;
}

export interface ChartSummary {
  underlying: string;
  current_price: number;
  total_trades: number;
  stock_trades: number;
  option_trades: number;
  buy_count: number;
  sell_count: number;
  total_realized_pnl: number;
  avg_buy_price: number;
  avg_sell_price: number;
}

export interface ReviewChartData {
  symbol: string;
  ohlc: OHLCData[];
  trades: ChartTrade[];
  summary: ChartSummary;
}

export interface GroupedSymbol {
  underlying: string;
  stock_trades: number;
  option_trades: number;
  total_pnl: number;
  symbols: string[];
}


export interface SyncResult {
  success: boolean;
  trades_synced: number;
  positions_synced: number;
  message: string;
}

export interface Settings {
  language: string;
  theme: string;
  ibkr_configured: boolean;
  ai_configured: boolean;
}

// 績效報告
export interface PerformanceReport {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  best_trade: number;
  worst_trade: number;
  pnl_by_symbol: Record<string, number>;
  pnl_by_hour: Record<number, number>;
  warnings: string[];
}

// 策略模擬
export interface StrategySimulationRequest {
  asset_type: 'stock' | 'option' | 'futures';
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  iv?: number;
  upcoming_events?: string;
  goal: 'add_position' | 'take_profit' | 'hedge' | 'spread';
}

export interface StrategyRecommendation {
  strategy: string;
  description: string;
  risk_level: string;
  expected_return: string;
}

// 選擇權顧問
export interface OptionsAdviceRequest {
  symbol: string;
  current_price: number;
  market_view: 'bullish' | 'bearish' | 'neutral' | 'volatile';
  time_horizon: string;
  risk_tolerance: 'conservative' | 'moderate' | 'aggressive';
  capital: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  beta?: number;
}

// 市場數據
export interface MarketQuote {
  symbol: string;
  current_price: number;
  previous_close?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  beta?: number;
  market_cap?: number;
  pe_ratio?: number;
}

// 回測
export interface BacktestSummary {
  name: string;
  path: string;
  size: number;
  num_strategies: number;
}

// 錯誤卡片
export interface MistakeCard {
  id: number;
  symbol: string;
  date: string;
  error_type: string;
  description: string;
  lesson: string;
  emotional_state?: string;
}

// API Functions

export const apiClient = {
  // Health
  async healthCheck() {
    const { data } = await api.get('/api/health');
    return data;
  },

  // Trades
  async getTrades(params?: { symbol?: string; limit?: number }) {
    const { data } = await api.get<Trade[]>('/api/trades', { params });
    return data;
  },

  async getSymbols() {
    const { data } = await api.get<{ symbols: string[] }>('/api/trades/symbols');
    return data.symbols;
  },

  async getPnlBySymbol() {
    const { data } = await api.get<{ pnl_by_symbol: Record<string, number> }>('/api/trades/pnl-by-symbol');
    return data.pnl_by_symbol;
  },

  // 交易檢討：K 線圖 + 買賣點
  async getReviewChartData(underlying: string, period: string = '1y') {
    const { data } = await api.get<ReviewChartData>(`/api/review/chart/${underlying}`, {
      params: { period }
    });
    return data;
  },

  async getGroupedSymbols() {
    const { data } = await api.get<GroupedSymbol[]>('/api/symbols/grouped');
    return data;
  },


  // Statistics
  async getStatistics(params?: { start_date?: string; end_date?: string }) {
    const { data } = await api.get<Statistics>('/api/statistics', { params });
    return data;
  },

  async getEquityCurve(params?: { start_date?: string; end_date?: string }) {
    const { data } = await api.get<{ data: EquityCurvePoint[] }>('/api/equity-curve', { params });
    return data.data;
  },

  // Portfolio
  async getPortfolio() {
    const { data } = await api.get<PortfolioOverview>('/api/portfolio');
    return data;
  },

  // IBKR
  async syncIBKR() {
    const { data } = await api.post<SyncResult>('/api/ibkr/sync');
    return data;
  },

  async getCashBalance() {
    const { data } = await api.get<CashBalance>('/api/ibkr/cash');
    return data;
  },

  // AI
  async aiChat(message: string, symbol?: string, sessionId?: string) {
    const { data } = await api.post<AIResponse>('/api/ai/chat', {
      message,
      symbol,
      session_id: sessionId,
    });
    return data;
  },

  async analyzePortfolio() {
    const { data } = await api.post<{ analysis: string }>('/api/ai/analyze-portfolio');
    return data.analysis;
  },

  // Settings
  async getSettings() {
    const { data } = await api.get<Settings>('/api/settings');
    return data;
  },

  async updateSettings(settings: { language?: string; theme?: string }) {
    const { data } = await api.put('/api/settings', null, { params: settings });
    return data;
  },

  // Maintenance
  async recalculatePnL() {
    const { data } = await api.post('/api/maintenance/recalculate-pnl');
    return data;
  },

  async clearDatabase() {
    const { data } = await api.delete('/api/maintenance/clear-database');
    return data;
  },

  // ========== 新增的 API ==========

  // 績效報告
  async getPerformanceReport() {
    const { data } = await api.get<PerformanceReport>('/api/report/performance');
    return data;
  },

  async getAIPerformanceReview() {
    const { data } = await api.post<{ review: string }>('/api/report/ai-review');
    return data.review;
  },

  // 策略模擬
  async simulateStrategy(request: StrategySimulationRequest) {
    const { data } = await api.post<{ recommendations: StrategyRecommendation[] }>('/api/strategy/simulate', request);
    return data.recommendations;
  },

  async getAIStrategyAdvice(request: StrategySimulationRequest) {
    const { data } = await api.post<{ advice: string }>('/api/strategy/ai-advice', request);
    return data.advice;
  },

  // 選擇權顧問
  async getOptionsAdvice(request: OptionsAdviceRequest) {
    const { data } = await api.post<{ advice: string }>('/api/options/advice', request);
    return data.advice;
  },

  // Portfolio AI
  async getPortfolioAIAnalysis(includeReports: boolean = true) {
    const { data } = await api.post<{ analysis: string }>('/api/portfolio/ai-analysis', {
      include_reports: includeReports,
    });
    return data.analysis;
  },

  // 回測
  async listBacktests() {
    const { data } = await api.get<{ backtests: BacktestSummary[] }>('/api/lab/backtests');
    return data.backtests;
  },

  async getBacktestResult(filename: string) {
    const { data } = await api.get<{ data: Record<string, unknown>[]; summary: Record<string, unknown> }>(
      `/api/lab/backtest/${filename}`
    );
    return data;
  },

  // 錯誤卡片
  async getMistakeCards() {
    const { data } = await api.get<{ cards: MistakeCard[] }>('/api/mistakes');
    return data.cards;
  },

  async addMistakeCard(card: Omit<MistakeCard, 'id'>) {
    const { data } = await api.post<{ id: number; message: string }>('/api/mistakes', card);
    return data;
  },

  // 市場數據
  async getMarketQuote(symbol: string) {
    const { data } = await api.get<MarketQuote>(`/api/market/quote/${symbol}`);
    return data;
  },

  async getMarketHistory(symbol: string, period: string = '1mo') {
    const { data } = await api.get<{ data: { date: string; open: number; high: number; low: number; close: number; volume: number }[] }>(
      `/api/market/history/${symbol}`,
      { params: { period } }
    );
    return data.data;
  },

  // ========== MFE/MAE 分析 ==========
  async getMFEMAEStats() {
    const { data } = await api.get<{ stats: MFEMAEStats }>('/api/mfe-mae/stats');
    return data.stats;
  },

  async getMFEMAERecords(symbol?: string) {
    const { data } = await api.get<{ records: MFEMAERecord[] }>('/api/mfe-mae/records', {
      params: symbol ? { symbol } : undefined
    });
    return data.records;
  },

  async calculateMFEMAE(symbol?: string) {
    const { data } = await api.post<{ success: boolean; calculated_count: number; results: MFEMAERecord[] }>(
      '/api/mfe-mae/calculate',
      null,
      { params: symbol ? { symbol } : undefined }
    );
    return data;
  },

  async getMFEMAEAnalysis() {
    const { data } = await api.get<{ analysis: MFEMAEAnalysis }>('/api/mfe-mae/analysis');
    return data.analysis;
  },

  async getMFEMAEAIAdvice(symbol?: string) {
    const { data } = await api.post<{ advice: string }>('/api/mfe-mae/ai-advice', null, {
      params: symbol ? { symbol } : undefined
    });
    return data.advice;
  },

  // ========== 交易計劃 ==========
  async getTradePlans(status?: string, symbol?: string) {
    const { data } = await api.get<{ plans: TradePlan[] }>('/api/plans', {
      params: { status, symbol }
    });
    return data.plans;
  },

  async getTradePlan(planId: number) {
    const { data } = await api.get<{ plan: TradePlan }>(`/api/plans/${planId}`);
    return data.plan;
  },

  async createTradePlan(plan: TradePlanInput) {
    const { data } = await api.post<{ plan_id: number; message: string }>('/api/plans', plan);
    return data;
  },

  async updateTradePlan(planId: number, updates: Partial<TradePlanInput>) {
    const { data } = await api.put<{ message: string }>(`/api/plans/${planId}`, updates);
    return data;
  },

  async deleteTradePlan(planId: number) {
    const { data } = await api.delete<{ message: string }>(`/api/plans/${planId}`);
    return data;
  },

  async getPlanAIReview(planId: number) {
    const { data } = await api.post<{ review: string }>(`/api/plans/${planId}/ai-review`);
    return data.review;
  },

  async getPlanPostAnalysis(planId: number) {
    const { data } = await api.post<{ analysis: string }>(`/api/plans/${planId}/ai-post-analysis`);
    return data.analysis;
  },

  // ========== 交易日誌筆記 ==========
  async getTradeNotes(params?: { note_type?: string; symbol?: string; start_date?: string; end_date?: string; limit?: number }) {
    const { data } = await api.get<{ notes: TradeNote[] }>('/api/notes', { params });
    return data.notes;
  },

  async getTradeNote(noteId: number) {
    const { data } = await api.get<{ note: TradeNote }>(`/api/notes/${noteId}`);
    return data.note;
  },

  async createTradeNote(note: TradeNoteInput) {
    const { data } = await api.post<{ note_id: number; message: string }>('/api/notes', note);
    return data;
  },

  async updateTradeNote(noteId: number, updates: Partial<TradeNoteInput>) {
    const { data } = await api.put<{ message: string }>(`/api/notes/${noteId}`, updates);
    return data;
  },

  async deleteTradeNote(noteId: number) {
    const { data } = await api.delete<{ message: string }>(`/api/notes/${noteId}`);
    return data;
  },

  async getNoteAIAnalysis(noteId: number) {
    const { data } = await api.post<{ analysis: string }>(`/api/notes/${noteId}/ai-analyze`);
    return data.analysis;
  },

  async getDailySummary(date: string) {
    const { data } = await api.get<{ summary: DailySummary }>(`/api/notes/daily-summary/${date}`);
    return data.summary;
  },

  // ========== AI 綜合審查 ==========
  async getComprehensiveAIReview() {
    const { data } = await api.post<{ review: string }>('/api/ai/comprehensive-review');
    return data.review;
  },
};

// ========== 新增的類型定義 ==========

// MFE/MAE 類型
export interface MFEMAERecord {
  id?: number;
  trade_id: string;
  symbol: string;
  entry_date: string;
  exit_date?: string;
  entry_price: number;
  exit_price?: number;
  mfe?: number;  // Max Favorable Excursion (%)
  mae?: number;  // Max Adverse Excursion (%)
  mfe_price?: number;
  mae_price?: number;
  mfe_date?: string;
  mae_date?: string;
  realized_pnl?: number;
  trade_efficiency?: number;
  holding_days?: number;
  max_drawdown_from_peak?: number;
}

export interface MFEMAEStats {
  total_trades: number;
  avg_mfe?: number;
  avg_mae?: number;
  avg_efficiency?: number;
  max_mfe?: number;
  max_mae?: number;
  avg_holding_days?: number;
  efficient_trades?: number;
  inefficient_trades?: number;
}

export interface MFEMAEAnalysis {
  total_trades: number;
  avg_mfe: number;
  avg_mae: number;
  avg_efficiency: number;
  avg_holding_days: number;
  efficient_count: number;
  inefficient_count: number;
  efficiency_rate: number;
  large_mae_count: number;
  missed_mfe_count: number;
  issues: string[];
  suggestions: string[];
}

// 交易計劃類型
export interface TradePlan {
  plan_id: number;
  symbol: string;
  direction: 'long' | 'short';
  status: 'pending' | 'executed' | 'cancelled' | 'expired';
  entry_trigger?: string;
  entry_price_min?: number;
  entry_price_max?: number;
  target_price?: number;
  stop_loss_price?: number;
  trailing_stop_pct?: number;
  position_size?: string;
  max_risk_amount?: number;
  risk_reward_ratio?: number;
  thesis?: string;
  market_condition?: string;
  key_levels?: string;
  valid_until?: string;
  created_at: string;
  updated_at: string;
  linked_trade_id?: string;
  execution_notes?: string;
  actual_entry_price?: number;
  actual_exit_price?: number;
  plan_vs_actual_diff?: number;
  ai_review?: string;
  ai_post_analysis?: string;
}

export interface TradePlanInput {
  symbol: string;
  direction?: 'long' | 'short';
  entry_trigger?: string;
  entry_price_min?: number;
  entry_price_max?: number;
  target_price?: number;
  stop_loss_price?: number;
  trailing_stop_pct?: number;
  position_size?: string;
  max_risk_amount?: number;
  thesis?: string;
  market_condition?: string;
  key_levels?: string;
  valid_until?: string;
  status?: string;
  execution_notes?: string;
  actual_entry_price?: number;
  actual_exit_price?: number;
}

// 交易筆記類型
export interface TradeNote {
  note_id: number;
  note_type: 'daily' | 'trade' | 'weekly' | 'monthly' | 'misc';
  date: string;
  symbol?: string;
  trade_id?: string;
  plan_id?: number;
  title?: string;
  content: string;
  mood?: string;
  confidence_level?: number;
  market_sentiment?: string;
  key_observations?: string[];
  lessons_learned?: string;
  action_items?: string[];
  tags?: string[];
  category?: string;
  ai_summary?: string;
  ai_suggestions?: string;
  ai_sentiment_score?: number;
  created_at: string;
  updated_at: string;
}

export interface TradeNoteInput {
  note_type?: 'daily' | 'trade' | 'weekly' | 'monthly' | 'misc';
  date: string;
  symbol?: string;
  trade_id?: string;
  plan_id?: number;
  title?: string;
  content: string;
  mood?: string;
  confidence_level?: number;
  market_sentiment?: string;
  key_observations?: string[];
  lessons_learned?: string;
  action_items?: string[];
  tags?: string[];
  category?: string;
}

export interface DailySummary {
  date: string;
  notes: TradeNote[];
  trades: Trade[];
  plans: TradePlan[];
  trade_count: number;
  total_pnl: number;
}
