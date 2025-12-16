'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import { Loader2, Brain, RefreshCw, FileText, PieChart, Shield, TrendingUp, AlertTriangle } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

export default function AIPage() {
  const { language } = useAppStore();
  const [includeReports, setIncludeReports] = useState(true);
  const [analysis, setAnalysis] = useState<string | null>(null);

  // 獲取投資組合數據
  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: apiClient.getPortfolio,
  });

  // 獲取統計數據
  const { data: stats } = useQuery({
    queryKey: ['statistics'],
    queryFn: () => apiClient.getStatistics(),
  });

  // AI 分析
  const analysisMutation = useMutation({
    mutationFn: () => apiClient.getPortfolioAIAnalysis(includeReports),
    onSuccess: (data) => {
      setAnalysis(data);
    },
  });

  const handleAnalyze = () => {
    analysisMutation.mutate();
  };

  if (portfolioLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{language === 'zh' ? '🧠 Portfolio AI 顧問' : '🧠 Portfolio AI Advisor'}</h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh'
            ? '基於實際持倉、市場走勢和研究報告，提供精準的風險管理與調整建議'
            : 'Get precise risk management and adjustment recommendations based on your positions, market trends, and research reports'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左側 - 持倉概覽 */}
        <div className="lg:col-span-1 space-y-6">
          {/* 帳戶摘要 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                {language === 'zh' ? '帳戶摘要' : 'Account Summary'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">{language === 'zh' ? '總市值' : 'Total Value'}</span>
                  <span className="font-bold">{formatCurrency(portfolio?.total_market_value || 0)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">{language === 'zh' ? '現金' : 'Cash'}</span>
                  <span className="font-bold">{formatCurrency(portfolio?.cash_balance || 0)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">{language === 'zh' ? '未實現盈虧' : 'Unrealized P&L'}</span>
                  <span className={cn(
                    'font-bold',
                    (portfolio?.total_unrealized_pnl || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'
                  )}>
                    {formatCurrency(portfolio?.total_unrealized_pnl || 0, true)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">{language === 'zh' ? '已實現盈虧' : 'Realized P&L'}</span>
                  <span className={cn(
                    'font-bold',
                    (portfolio?.total_realized_pnl || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'
                  )}>
                    {formatCurrency(portfolio?.total_realized_pnl || 0, true)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 持倉列表 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                {language === 'zh' ? '當前持倉' : 'Current Positions'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {portfolio?.positions && portfolio.positions.length > 0 ? (
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {portfolio.positions.map((pos, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium">{pos.symbol}</span>
                        <span className="text-sm text-gray-500">{pos.quantity} 股</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-500">
                          {formatCurrency(pos.avg_cost)} → {formatCurrency(pos.current_price || 0)}
                        </span>
                        <span className={cn(
                          'font-medium',
                          (pos.unrealized_pnl || 0) >= 0 ? 'text-emerald-500' : 'text-red-500'
                        )}>
                          {formatCurrency(pos.unrealized_pnl || 0, true)}
                        </span>
                      </div>
                      {pos.strategy && (
                        <div className="mt-1">
                          <span className="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded">
                            {pos.strategy}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">
                  {language === 'zh' ? '無持倉數據' : 'No positions'}
                </p>
              )}
            </CardContent>
          </Card>

          {/* 績效統計 */}
          {stats && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  {language === 'zh' ? '績效指標' : 'Performance Metrics'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">{language === 'zh' ? '總交易' : 'Total Trades'}</span>
                    <span>{stats.total_trades}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">{language === 'zh' ? '勝率' : 'Win Rate'}</span>
                    <span>{stats.win_rate.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">{language === 'zh' ? '獲利因子' : 'Profit Factor'}</span>
                    <span>{stats.profit_factor.toFixed(2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* 右側 - AI 分析 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 分析控制 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                {language === 'zh' ? 'AI 投資組合分析' : 'AI Portfolio Analysis'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeReports}
                      onChange={(e) => setIncludeReports(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm">
                      <FileText className="h-4 w-4 inline mr-1" />
                      {language === 'zh' ? '納入研究報告' : 'Include research reports'}
                    </span>
                  </label>
                </div>

                <Button
                  onClick={handleAnalyze}
                  disabled={analysisMutation.isPending}
                  size="lg"
                  className="w-full"
                >
                  {analysisMutation.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-5 w-5 mr-2" />
                  )}
                  {language === 'zh' ? '開始 AI 深度分析' : 'Start AI Analysis'}
                </Button>

                <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    {language === 'zh'
                      ? 'AI 將分析你的持倉風險、市場暴露、並提供避險策略和調整建議。'
                      : 'AI will analyze your position risk, market exposure, and provide hedging strategies and adjustment recommendations.'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* AI 分析結果 */}
          <Card className="min-h-[400px]">
            <CardHeader>
              <CardTitle>{language === 'zh' ? '📊 分析報告' : '📊 Analysis Report'}</CardTitle>
            </CardHeader>
            <CardContent>
              {analysis ? (
                <MarkdownRenderer content={analysis} />
              ) : (
                <div className="text-center py-16">
                  <Brain className="h-20 w-20 text-gray-200 dark:text-gray-700 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-500 mb-2">
                    {language === 'zh' ? '等待分析' : 'Awaiting Analysis'}
                  </h3>
                  <p className="text-gray-400 text-sm max-w-md mx-auto">
                    {language === 'zh'
                      ? '點擊上方「開始 AI 深度分析」按鈕，AI 將根據你的持倉和市場數據生成個人化的投資建議。'
                      : 'Click "Start AI Analysis" above. AI will generate personalized investment recommendations based on your positions and market data.'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
