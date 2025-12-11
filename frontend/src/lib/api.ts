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

  // Statistics
  async getStatistics() {
    const { data } = await api.get<Statistics>('/api/statistics');
    return data;
  },

  async getEquityCurve() {
    const { data } = await api.get<{ data: EquityCurvePoint[] }>('/api/equity-curve');
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
};

