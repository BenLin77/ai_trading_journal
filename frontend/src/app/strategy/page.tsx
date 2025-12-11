'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient, StrategySimulationRequest, StrategyRecommendation } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import { Loader2, TrendingUp, Shield, Target, Zap, Send } from 'lucide-react';

const GOALS = [
  { value: 'add_position', label: { zh: '加碼進場', en: 'Add Position' }, icon: TrendingUp },
  { value: 'take_profit', label: { zh: '獲利了結', en: 'Take Profit' }, icon: Target },
  { value: 'hedge', label: { zh: '對沖風險', en: 'Hedge' }, icon: Shield },
  { value: 'spread', label: { zh: '價差交易', en: 'Spread' }, icon: Zap },
] as const;

const ASSET_TYPES = [
  { value: 'stock', label: { zh: '股票', en: 'Stock' } },
  { value: 'option', label: { zh: '選擇權', en: 'Option' } },
  { value: 'futures', label: { zh: '期貨', en: 'Futures' } },
] as const;

export default function StrategyPage() {
  const { language } = useAppStore();

  // Form state
  const [assetType, setAssetType] = useState<'stock' | 'option' | 'futures'>('stock');
  const [symbol, setSymbol] = useState('AAPL');
  const [quantity, setQuantity] = useState(100);
  const [avgCost, setAvgCost] = useState(150);
  const [currentPrice, setCurrentPrice] = useState(155);
  const [iv, setIv] = useState(25);
  const [upcomingEvents, setUpcomingEvents] = useState('');
  const [goal, setGoal] = useState<'add_position' | 'take_profit' | 'hedge' | 'spread'>('add_position');

  const [recommendations, setRecommendations] = useState<StrategyRecommendation[]>([]);
  const [aiAdvice, setAiAdvice] = useState<string | null>(null);

  // 獲取市場報價
  const quoteMutation = useMutation({
    mutationFn: (sym: string) => apiClient.getMarketQuote(sym),
    onSuccess: (data) => {
      setCurrentPrice(data.current_price);
    },
  });

  // 策略模擬
  const simulateMutation = useMutation({
    mutationFn: (request: StrategySimulationRequest) => apiClient.simulateStrategy(request),
    onSuccess: (data) => {
      setRecommendations(data);
    },
  });

  // AI 策略建議
  const aiMutation = useMutation({
    mutationFn: (request: StrategySimulationRequest) => apiClient.getAIStrategyAdvice(request),
    onSuccess: (data) => {
      setAiAdvice(data);
    },
  });

  const handleFetchQuote = () => {
    quoteMutation.mutate(symbol);
  };

  const handleSimulate = () => {
    const request: StrategySimulationRequest = {
      asset_type: assetType,
      symbol,
      quantity,
      avg_cost: avgCost,
      current_price: currentPrice,
      iv,
      upcoming_events: upcomingEvents,
      goal,
    };
    simulateMutation.mutate(request);
  };

  const handleGetAIAdvice = () => {
    const request: StrategySimulationRequest = {
      asset_type: assetType,
      symbol,
      quantity,
      avg_cost: avgCost,
      current_price: currentPrice,
      iv,
      upcoming_events: upcomingEvents,
      goal,
    };
    aiMutation.mutate(request);
  };

  // 計算未實現盈虧
  const unrealizedPnl = (currentPrice - avgCost) * quantity;
  const pnlPct = avgCost > 0 ? ((currentPrice - avgCost) / avgCost) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{language === 'zh' ? '🎯 策略模擬' : '🎯 Strategy Simulation'}</h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? 'What-if 情境分析與策略建議' : 'What-if scenario analysis and strategy recommendations'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 輸入區 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>{language === 'zh' ? '📋 情境設定' : '📋 Scenario Setup'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 資產類型 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '資產類型' : 'Asset Type'}
              </label>
              <div className="flex gap-2">
                {ASSET_TYPES.map((at) => (
                  <button
                    key={at.value}
                    onClick={() => setAssetType(at.value as 'stock' | 'option' | 'futures')}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-sm transition-colors',
                      assetType === at.value
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                    )}
                  >
                    {at.label[language]}
                  </button>
                ))}
              </div>
            </div>

            {/* 標的代號 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '標的代號' : 'Symbol'}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                />
                <Button onClick={handleFetchQuote} disabled={quoteMutation.isPending} size="sm">
                  {quoteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : '📈'}
                </Button>
              </div>
            </div>

            {/* 持倉數量 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '持倉數量' : 'Quantity'}
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
            </div>

            {/* 平均成本 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '平均成本 ($)' : 'Avg Cost ($)'}
              </label>
              <input
                type="number"
                value={avgCost}
                onChange={(e) => setAvgCost(Number(e.target.value))}
                step="0.01"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
            </div>

            {/* 當前市價 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '當前市價 ($)' : 'Current Price ($)'}
              </label>
              <input
                type="number"
                value={currentPrice}
                onChange={(e) => setCurrentPrice(Number(e.target.value))}
                step="0.01"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
            </div>

            {/* IV */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                IV (%)
              </label>
              <input
                type="number"
                value={iv}
                onChange={(e) => setIv(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
              />
            </div>

            {/* 即將發生的事件 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '即將發生的事件' : 'Upcoming Events'}
              </label>
              <textarea
                value={upcomingEvents}
                onChange={(e) => setUpcomingEvents(e.target.value)}
                placeholder={language === 'zh' ? '例如：本週三財報、下週 FOMC' : 'e.g., Earnings Wed, FOMC next week'}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 min-h-[60px]"
              />
            </div>

            {/* 目標 */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                {language === 'zh' ? '我的目標' : 'My Goal'}
              </label>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map((g) => {
                  const Icon = g.icon;
                  return (
                    <button
                      key={g.value}
                      onClick={() => setGoal(g.value)}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
                        goal === g.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {g.label[language]}
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 結果區 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 當前持倉狀態 */}
          <Card>
            <CardHeader>
              <CardTitle>{language === 'zh' ? '📊 當前持倉狀態' : '📊 Current Position'}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-sm text-gray-500">{language === 'zh' ? '市值' : 'Market Value'}</p>
                  <p className="text-xl font-bold">{formatCurrency(currentPrice * quantity)}</p>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-sm text-gray-500">{language === 'zh' ? '浮動盈虧' : 'Unrealized P&L'}</p>
                  <p className={cn('text-xl font-bold', unrealizedPnl >= 0 ? 'text-emerald-500' : 'text-red-500')}>
                    {formatCurrency(unrealizedPnl, true)}
                  </p>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-sm text-gray-500">{language === 'zh' ? '報酬率' : 'Return'}</p>
                  <p className={cn('text-xl font-bold', pnlPct >= 0 ? 'text-emerald-500' : 'text-red-500')}>
                    {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                  </p>
                </div>
              </div>

              <div className="mt-4 flex gap-3">
                <Button onClick={handleSimulate} disabled={simulateMutation.isPending} className="flex-1">
                  {simulateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Target className="h-4 w-4 mr-2" />
                  )}
                  {language === 'zh' ? '取得策略建議' : 'Get Recommendations'}
                </Button>
                <Button onClick={handleGetAIAdvice} disabled={aiMutation.isPending} variant="secondary" className="flex-1">
                  {aiMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Send className="h-4 w-4 mr-2" />
                  )}
                  {language === 'zh' ? 'AI 深度分析' : 'AI Analysis'}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 策略建議 */}
          {recommendations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{language === 'zh' ? '🤖 策略建議' : '🤖 Strategy Recommendations'}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recommendations.map((rec, idx) => (
                    <div key={idx} className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-lg">{rec.strategy}</h3>
                        <span className={cn(
                          'px-2 py-0.5 rounded text-xs',
                          rec.risk_level === '低' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600' :
                            rec.risk_level === '中等' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600' :
                              'bg-red-100 dark:bg-red-900/30 text-red-600'
                        )}>
                          {language === 'zh' ? `風險: ${rec.risk_level}` : `Risk: ${rec.risk_level}`}
                        </span>
                      </div>
                      <p className="text-gray-600 dark:text-gray-400 mb-2">{rec.description}</p>
                      <p className="text-sm text-blue-600 dark:text-blue-400">
                        {language === 'zh' ? `預期收益: ${rec.expected_return}` : `Expected: ${rec.expected_return}`}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* AI 深度分析結果 */}
          {aiAdvice && (
            <Card>
              <CardHeader>
                <CardTitle>{language === 'zh' ? '🧠 AI 策略師分析' : '🧠 AI Strategist Analysis'}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose dark:prose-invert max-w-none">
                  <div className="whitespace-pre-wrap text-sm">{aiAdvice}</div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
