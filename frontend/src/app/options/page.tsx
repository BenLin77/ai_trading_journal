'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient, OptionsAdviceRequest } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import { Loader2, TrendingUp, TrendingDown, Minus, Zap, DollarSign } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

const MARKET_VIEWS = [
  { value: 'bullish', label: { zh: '📈 看漲', en: '📈 Bullish' }, color: 'text-emerald-500' },
  { value: 'bearish', label: { zh: '📉 看跌', en: '📉 Bearish' }, color: 'text-red-500' },
  { value: 'neutral', label: { zh: '↔️ 中性', en: '↔️ Neutral' }, color: 'text-gray-500' },
  { value: 'volatile', label: { zh: '📊 高波動', en: '📊 Volatile' }, color: 'text-purple-500' },
] as const;

const TIME_HORIZONS = [
  { value: '1-2週', label: { zh: '1-2 週', en: '1-2 Weeks' } },
  { value: '3-4週', label: { zh: '3-4 週', en: '3-4 Weeks' } },
  { value: '1-2個月', label: { zh: '1-2 個月', en: '1-2 Months' } },
  { value: '3個月以上', label: { zh: '3 個月以上', en: '3+ Months' } },
] as const;

const RISK_LEVELS = [
  { value: 'conservative', label: { zh: '保守', en: 'Conservative' } },
  { value: 'moderate', label: { zh: '中等', en: 'Moderate' } },
  { value: 'aggressive', label: { zh: '積極', en: 'Aggressive' } },
] as const;

export default function OptionsPage() {
  const { language } = useAppStore();

  // Form state
  const [symbol, setSymbol] = useState('AAPL');
  const [currentPrice, setCurrentPrice] = useState(0);
  const [marketView, setMarketView] = useState<'bullish' | 'bearish' | 'neutral' | 'volatile'>('bullish');
  const [timeHorizon, setTimeHorizon] = useState('3-4週');
  const [riskTolerance, setRiskTolerance] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate');
  const [capital, setCapital] = useState(5000);
  const [fiftyTwoWeekHigh, setFiftyTwoWeekHigh] = useState<number | undefined>();
  const [fiftyTwoWeekLow, setFiftyTwoWeekLow] = useState<number | undefined>();
  const [beta, setBeta] = useState<number | undefined>();

  const [advice, setAdvice] = useState<string | null>(null);

  // 獲取市場報價
  const quoteMutation = useMutation({
    mutationFn: (sym: string) => apiClient.getMarketQuote(sym),
    onSuccess: (data) => {
      setCurrentPrice(data.current_price);
      setFiftyTwoWeekHigh(data.fifty_two_week_high);
      setFiftyTwoWeekLow(data.fifty_two_week_low);
      setBeta(data.beta);
    },
  });

  // 獲取選擇權建議
  const adviceMutation = useMutation({
    mutationFn: (request: OptionsAdviceRequest) => apiClient.getOptionsAdvice(request),
    onSuccess: (data) => {
      setAdvice(data);
    },
  });

  const handleFetchQuote = () => {
    quoteMutation.mutate(symbol);
  };

  const handleGetAdvice = () => {
    if (!currentPrice) {
      alert(language === 'zh' ? '請先載入標的數據' : 'Please load symbol data first');
      return;
    }

    const request: OptionsAdviceRequest = {
      symbol,
      current_price: currentPrice,
      market_view: marketView,
      time_horizon: timeHorizon,
      risk_tolerance: riskTolerance,
      capital,
      fifty_two_week_high: fiftyTwoWeekHigh,
      fifty_two_week_low: fiftyTwoWeekLow,
      beta,
    };
    adviceMutation.mutate(request);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{language === 'zh' ? '💡 選擇權 AI 顧問' : '💡 Options AI Advisor'}</h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? '根據你的市場看法，AI 推薦最適合的選擇權策略' : 'Get AI-powered options strategy recommendations based on your market outlook'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左側輸入區 */}
        <div className="space-y-6">
          {/* 標的資訊 */}
          <Card>
            <CardHeader>
              <CardTitle>{language === 'zh' ? '📊 標的資訊' : '📊 Symbol Info'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
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
                  <Button onClick={handleFetchQuote} disabled={quoteMutation.isPending}>
                    {quoteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : '📈 載入'}
                  </Button>
                </div>
              </div>

              {currentPrice > 0 && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                    <p className="text-xs text-gray-500">{language === 'zh' ? '即時股價' : 'Current Price'}</p>
                    <p className="text-lg font-bold">{formatCurrency(currentPrice)}</p>
                  </div>
                  {fiftyTwoWeekHigh && (
                    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                      <p className="text-xs text-gray-500">52W High</p>
                      <p className="text-lg font-bold text-emerald-500">{formatCurrency(fiftyTwoWeekHigh)}</p>
                    </div>
                  )}
                  {fiftyTwoWeekLow && (
                    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                      <p className="text-xs text-gray-500">52W Low</p>
                      <p className="text-lg font-bold text-red-500">{formatCurrency(fiftyTwoWeekLow)}</p>
                    </div>
                  )}
                  {beta && (
                    <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                      <p className="text-xs text-gray-500">Beta</p>
                      <p className="text-lg font-bold">{beta.toFixed(2)}</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* 市場看法 */}
          <Card>
            <CardHeader>
              <CardTitle>{language === 'zh' ? '🎯 市場看法' : '🎯 Market Outlook'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '方向預期' : 'Direction'}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {MARKET_VIEWS.map((mv) => (
                    <button
                      key={mv.value}
                      onClick={() => setMarketView(mv.value as 'bullish' | 'bearish' | 'neutral' | 'volatile')}
                      className={cn(
                        'px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                        marketView === mv.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                      )}
                    >
                      {mv.label[language]}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '時間範圍' : 'Time Horizon'}
                </label>
                <select
                  value={timeHorizon}
                  onChange={(e) => setTimeHorizon(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                >
                  {TIME_HORIZONS.map((th) => (
                    <option key={th.value} value={th.value}>
                      {th.label[language]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '風險承受度' : 'Risk Tolerance'}
                </label>
                <div className="flex gap-2">
                  {RISK_LEVELS.map((rl) => (
                    <button
                      key={rl.value}
                      onClick={() => setRiskTolerance(rl.value as 'conservative' | 'moderate' | 'aggressive')}
                      className={cn(
                        'flex-1 px-3 py-2 rounded-lg text-sm transition-colors',
                        riskTolerance === rl.value
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                      )}
                    >
                      {rl.label[language]}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                  {language === 'zh' ? '可用資金 ($)' : 'Available Capital ($)'}
                </label>
                <input
                  type="number"
                  value={capital}
                  onChange={(e) => setCapital(Number(e.target.value))}
                  step="100"
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                />
              </div>

              <Button
                onClick={handleGetAdvice}
                disabled={adviceMutation.isPending || !currentPrice}
                className="w-full"
                size="lg"
              >
                {adviceMutation.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                ) : (
                  <Zap className="h-5 w-5 mr-2" />
                )}
                {language === 'zh' ? '取得 AI 策略建議' : 'Get AI Strategy Advice'}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* 右側結果區 */}
        <div className="space-y-6">
          {/* AI 建議結果 */}
          <Card className="h-full">
            <CardHeader>
              <CardTitle>{language === 'zh' ? '🤖 AI 策略建議' : '🤖 AI Strategy Advice'}</CardTitle>
            </CardHeader>
            <CardContent>
              {advice ? (
                <MarkdownRenderer content={advice} />
              ) : (
                <div className="text-center py-12">
                  <DollarSign className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">
                    {language === 'zh'
                      ? '填寫左側資訊並點擊「取得 AI 策略建議」'
                      : 'Fill in the information and click "Get AI Strategy Advice"'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 策略快速參考 */}
          <Card>
            <CardHeader>
              <CardTitle>{language === 'zh' ? '📚 策略速查表' : '📚 Strategy Quick Reference'}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-emerald-600 mb-1">
                    {language === 'zh' ? '看漲策略' : 'Bullish Strategies'}
                  </h4>
                  <ul className="text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Long Call - {language === 'zh' ? '最簡單，適合強烈看漲' : 'Simple, strong bullish'}</li>
                    <li>• Bull Call Spread - {language === 'zh' ? '降低成本，限制獲利' : 'Lower cost, capped profit'}</li>
                    <li>• Cash-Secured Put - {language === 'zh' ? '收權利金，願意買進' : 'Premium income, willing to buy'}</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-red-600 mb-1">
                    {language === 'zh' ? '看跌策略' : 'Bearish Strategies'}
                  </h4>
                  <ul className="text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Long Put - {language === 'zh' ? '保護或投機' : 'Protection or speculation'}</li>
                    <li>• Bear Put Spread - {language === 'zh' ? '降低成本' : 'Lower cost'}</li>
                    <li>• Covered Call - {language === 'zh' ? '持股收租' : 'Income from holdings'}</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-600 mb-1">
                    {language === 'zh' ? '中性策略' : 'Neutral Strategies'}
                  </h4>
                  <ul className="text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Iron Condor - {language === 'zh' ? '賺時間價值' : 'Time decay profit'}</li>
                    <li>• Butterfly - {language === 'zh' ? '低成本，大獲利（低機率）' : 'Low cost, high reward'}</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
