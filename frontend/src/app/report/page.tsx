'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient, PerformanceReport } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn, formatPercent } from '@/lib/utils';
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, Award, Target } from 'lucide-react';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

export default function ReportPage() {
  const { language } = useAppStore();
  const [aiReview, setAiReview] = useState<string | null>(null);

  const { data: report, isLoading } = useQuery({
    queryKey: ['performance-report'],
    queryFn: apiClient.getPerformanceReport,
  });

  const aiReviewMutation = useMutation({
    mutationFn: apiClient.getAIPerformanceReview,
    onSuccess: (data) => {
      setAiReview(data);
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">{language === 'zh' ? '無績效數據' : 'No performance data'}</p>
      </div>
    );
  }

  // 排序的標的盈虧
  const sortedSymbolPnl = Object.entries(report.pnl_by_symbol).sort((a, b) => b[1] - a[1]);
  const bestSymbol = sortedSymbolPnl[0];
  const worstSymbol = sortedSymbolPnl[sortedSymbolPnl.length - 1];

  // 排序的時段盈虧
  const sortedHourPnl = Object.entries(report.pnl_by_hour).sort((a, b) => Number(a[0]) - Number(b[0]));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{language === 'zh' ? '📊 績效成績單' : '📊 Performance Report'}</h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? '長期績效追蹤與 AI 改進建議' : 'Long-term performance tracking and AI improvement suggestions'}
        </p>
      </div>

      {/* 警告提示 */}
      {report.warnings.length > 0 && (
        <div className="space-y-2">
          {report.warnings.map((warning, idx) => (
            <div key={idx} className="flex items-center gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
              <p className="text-yellow-800 dark:text-yellow-200">{warning}</p>
            </div>
          ))}
        </div>
      )}

      {/* 核心 KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{language === 'zh' ? '總盈虧' : 'Total P&L'}</p>
                <p className={cn('text-2xl font-bold', report.total_pnl >= 0 ? 'text-emerald-500' : 'text-red-500')}>
                  {formatCurrency(report.total_pnl, true)}
                </p>
              </div>
              {report.total_pnl >= 0 ? (
                <TrendingUp className="h-8 w-8 text-emerald-500 opacity-50" />
              ) : (
                <TrendingDown className="h-8 w-8 text-red-500 opacity-50" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{language === 'zh' ? '勝率' : 'Win Rate'}</p>
                <p className="text-2xl font-bold">{report.win_rate.toFixed(1)}%</p>
                <p className="text-xs text-gray-400">
                  {report.wins}W / {report.losses}L
                </p>
              </div>
              <Target className="h-8 w-8 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-sm text-gray-500">{language === 'zh' ? '獲利因子' : 'Profit Factor'}</p>
              <p className={cn('text-2xl font-bold', report.profit_factor >= 1.5 ? 'text-emerald-500' : report.profit_factor >= 1 ? 'text-yellow-500' : 'text-red-500')}>
                {report.profit_factor.toFixed(2)}
              </p>
              <p className="text-xs text-gray-400">
                {report.profit_factor >= 1.5 ? '✅ 優良' : report.profit_factor >= 1 ? '⚠️ 及格' : '❌ 需改善'}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-sm text-gray-500">{language === 'zh' ? '賺賠比' : 'Risk/Reward'}</p>
              <p className="text-2xl font-bold">
                {report.avg_loss !== 0 ? (report.avg_win / Math.abs(report.avg_loss)).toFixed(2) : '∞'}
              </p>
              <p className="text-xs text-gray-400">
                {language === 'zh' ? `贏 ${formatCurrency(report.avg_win)} / 輸 ${formatCurrency(report.avg_loss)}` : `W ${formatCurrency(report.avg_win)} / L ${formatCurrency(report.avg_loss)}`}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 詳細統計 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 按標的分析 */}
        <Card>
          <CardHeader>
            <CardTitle>{language === 'zh' ? '📈 標的盈虧排行' : '📈 P&L by Symbol'}</CardTitle>
          </CardHeader>
          <CardContent>
            {sortedSymbolPnl.length > 0 ? (
              <div className="space-y-3">
                {/* 最佳和最差 */}
                {bestSymbol && (
                  <div className="flex items-center justify-between p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Award className="h-5 w-5 text-emerald-500" />
                      <span className="font-medium">{bestSymbol[0]}</span>
                    </div>
                    <span className="text-emerald-600 font-bold">{formatCurrency(bestSymbol[1], true)}</span>
                  </div>
                )}
                {worstSymbol && worstSymbol[1] < 0 && (
                  <div className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <div className="flex items-center gap-2">
                      <TrendingDown className="h-5 w-5 text-red-500" />
                      <span className="font-medium">{worstSymbol[0]}</span>
                    </div>
                    <span className="text-red-600 font-bold">{formatCurrency(worstSymbol[1], true)}</span>
                  </div>
                )}

                {/* 完整列表 */}
                <div className="max-h-48 overflow-y-auto space-y-2 mt-4">
                  {sortedSymbolPnl.map(([symbol, pnl]) => (
                    <div key={symbol} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
                      <span className="text-sm">{symbol}</span>
                      <span className={cn('text-sm font-medium', pnl >= 0 ? 'text-emerald-500' : 'text-red-500')}>
                        {formatCurrency(pnl, true)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">{language === 'zh' ? '無數據' : 'No data'}</p>
            )}
          </CardContent>
        </Card>

        {/* 按時段分析 */}
        <Card>
          <CardHeader>
            <CardTitle>{language === 'zh' ? '⏰ 時段盈虧分析' : '⏰ P&L by Hour'}</CardTitle>
          </CardHeader>
          <CardContent>
            {sortedHourPnl.length > 0 ? (
              <div className="space-y-2">
                {sortedHourPnl.map(([hour, pnl]) => {
                  const maxPnl = Math.max(...Object.values(report.pnl_by_hour).map(Math.abs));
                  const barWidth = maxPnl > 0 ? (Math.abs(pnl) / maxPnl) * 100 : 0;

                  return (
                    <div key={hour} className="flex items-center gap-3">
                      <span className="text-sm text-gray-500 w-12">{hour}:00</span>
                      <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden relative">
                        <div
                          className={cn(
                            'h-full transition-all',
                            pnl >= 0 ? 'bg-emerald-500' : 'bg-red-500'
                          )}
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                      <span className={cn('text-sm font-medium w-20 text-right', pnl >= 0 ? 'text-emerald-500' : 'text-red-500')}>
                        {formatCurrency(pnl, true)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">{language === 'zh' ? '無數據' : 'No data'}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 極值統計 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-gray-500">{language === 'zh' ? '最佳單筆' : 'Best Trade'}</p>
            <p className="text-xl font-bold text-emerald-500">{formatCurrency(report.best_trade, true)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-gray-500">{language === 'zh' ? '最差單筆' : 'Worst Trade'}</p>
            <p className="text-xl font-bold text-red-500">{formatCurrency(report.worst_trade, true)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-gray-500">{language === 'zh' ? '平均獲利' : 'Avg Win'}</p>
            <p className="text-xl font-bold text-emerald-500">{formatCurrency(report.avg_win)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-gray-500">{language === 'zh' ? '平均虧損' : 'Avg Loss'}</p>
            <p className="text-xl font-bold text-red-500">{formatCurrency(report.avg_loss)}</p>
          </CardContent>
        </Card>
      </div>

      {/* AI 績效評語 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{language === 'zh' ? '🧠 AI 績效教練評語' : '🧠 AI Performance Coach'}</CardTitle>
          <Button onClick={() => aiReviewMutation.mutate()} disabled={aiReviewMutation.isPending}>
            {aiReviewMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {language === 'zh' ? '取得 AI 評語' : 'Get AI Review'}
          </Button>
        </CardHeader>
        <CardContent>
          {aiReview ? (
            <MarkdownRenderer content={aiReview} />
          ) : (
            <p className="text-gray-500 text-center py-8">
              {language === 'zh' ? '點擊上方按鈕取得 AI 教練的個人化績效評語' : 'Click the button above to get personalized AI performance review'}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
