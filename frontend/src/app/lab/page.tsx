'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient, BacktestSummary } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import { Loader2, FileBarChart, TrendingUp, AlertTriangle, CheckCircle, BarChart3 } from 'lucide-react';

export default function LabPage() {
  const { language } = useAppStore();
  const [selectedBacktest, setSelectedBacktest] = useState<string | null>(null);
  const [backtestData, setBacktestData] = useState<{ data: Record<string, unknown>[]; summary: Record<string, unknown> } | null>(null);

  // 列出可用的回測結果
  const { data: backtests, isLoading: listLoading } = useQuery({
    queryKey: ['backtests'],
    queryFn: apiClient.listBacktests,
  });

  // 載入回測結果
  const loadMutation = useMutation({
    mutationFn: (filename: string) => apiClient.getBacktestResult(filename),
    onSuccess: (data) => {
      setBacktestData(data);
    },
  });

  const handleLoadBacktest = (filename: string) => {
    setSelectedBacktest(filename);
    loadMutation.mutate(filename);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{language === 'zh' ? '🔬 策略實驗室' : '🔬 Strategy Lab'}</h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? '載入並分析回測結果，識別穩健策略' : 'Load and analyze backtest results, identify robust strategies'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 側邊欄 - 回測列表 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileBarChart className="h-5 w-5" />
              {language === 'zh' ? '回測結果' : 'Backtest Results'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {listLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
              </div>
            ) : backtests && backtests.length > 0 ? (
              <div className="space-y-2">
                {backtests.map((bt) => (
                  <button
                    key={bt.name}
                    onClick={() => handleLoadBacktest(bt.name)}
                    className={cn(
                      'w-full text-left p-3 rounded-lg transition-colors',
                      selectedBacktest === bt.name
                        ? 'bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700'
                        : 'bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-700'
                    )}
                  >
                    <p className="font-medium truncate">{bt.name}</p>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>{(bt.size / 1024).toFixed(1)} KB</span>
                      <span>{bt.num_strategies} {language === 'zh' ? '個策略' : 'strategies'}</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileBarChart className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">
                  {language === 'zh' ? '尚無回測結果' : 'No backtest results yet'}
                </p>
                <p className="text-gray-400 text-xs mt-2">
                  {language === 'zh'
                    ? '請在 records/ 資料夾放入 Parquet 回測檔案'
                    : 'Place Parquet backtest files in records/ folder'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 主要內容區 */}
        <div className="lg:col-span-3 space-y-6">
          {loadMutation.isPending ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : backtestData ? (
            <>
              {/* 摘要統計 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-6 text-center">
                    <BarChart3 className="h-8 w-8 text-blue-500 mx-auto mb-2 opacity-50" />
                    <p className="text-sm text-gray-500">{language === 'zh' ? '總策略數' : 'Total Strategies'}</p>
                    <p className="text-2xl font-bold">{backtestData.summary.total_strategies as number || backtestData.data.length}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6 text-center">
                    <TrendingUp className="h-8 w-8 text-emerald-500 mx-auto mb-2 opacity-50" />
                    <p className="text-sm text-gray-500">{language === 'zh' ? '最佳 Sharpe' : 'Best Sharpe'}</p>
                    <p className="text-2xl font-bold text-emerald-500">
                      {(backtestData.summary.best_sharpe as number)?.toFixed(2) || 'N/A'}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6 text-center">
                    <CheckCircle className="h-8 w-8 text-blue-500 mx-auto mb-2 opacity-50" />
                    <p className="text-sm text-gray-500">{language === 'zh' ? '穩定參數組合' : 'Stable Params'}</p>
                    <p className="text-2xl font-bold">{backtestData.summary.stable_params_count as number || 0}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-6 text-center">
                    <AlertTriangle className={cn(
                      'h-8 w-8 mx-auto mb-2 opacity-50',
                      backtestData.summary.is_overfitted ? 'text-red-500' : 'text-emerald-500'
                    )} />
                    <p className="text-sm text-gray-500">{language === 'zh' ? '過擬合風險' : 'Overfit Risk'}</p>
                    <p className={cn(
                      'text-2xl font-bold',
                      backtestData.summary.is_overfitted ? 'text-red-500' : 'text-emerald-500'
                    )}>
                      {backtestData.summary.is_overfitted
                        ? (language === 'zh' ? '高' : 'High')
                        : (language === 'zh' ? '低' : 'Low')}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* 策略數據表格 */}
              <Card>
                <CardHeader>
                  <CardTitle>{language === 'zh' ? '📊 策略績效數據' : '📊 Strategy Performance Data'}</CardTitle>
                </CardHeader>
                <CardContent>
                  {backtestData.data.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 dark:border-gray-700">
                            {Object.keys(backtestData.data[0]).slice(0, 8).map((key) => (
                              <th key={key} className="text-left py-2 px-2 font-medium text-gray-600 dark:text-gray-400">
                                {key}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {backtestData.data.slice(0, 20).map((row, idx) => (
                            <tr key={idx} className="border-b border-gray-100 dark:border-gray-800">
                              {Object.values(row).slice(0, 8).map((val, vidx) => (
                                <td key={vidx} className="py-2 px-2">
                                  {typeof val === 'number'
                                    ? val.toFixed(2)
                                    : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {backtestData.data.length > 20 && (
                        <p className="text-center text-gray-500 text-sm mt-4">
                          {language === 'zh'
                            ? `顯示前 20 筆，共 ${backtestData.data.length} 筆`
                            : `Showing 20 of ${backtestData.data.length} rows`}
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">{language === 'zh' ? '無數據' : 'No data'}</p>
                  )}
                </CardContent>
              </Card>

              {/* 參數穩定性分析提示 */}
              <Card>
                <CardHeader>
                  <CardTitle>{language === 'zh' ? '🗻 參數穩定性分析' : '🗻 Parameter Stability Analysis'}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                    <p className="text-blue-800 dark:text-blue-200">
                      {language === 'zh'
                        ? '💡 提示：尋找「參數高原」- 即在一系列相鄰參數組合中都能維持良好績效的區域。這類策略更可能在實戰中穩定獲利。'
                        : '💡 Tip: Look for "parameter plateaus" - regions where performance remains robust across a range of nearby parameter combinations. Such strategies are more likely to be profitable in live trading.'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <BarChart3 className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400 mb-2">
                    {language === 'zh' ? '選擇回測結果' : 'Select a Backtest Result'}
                  </h3>
                  <p className="text-gray-500 text-sm">
                    {language === 'zh'
                      ? '從左側選擇一個回測檔案來查看詳細分析'
                      : 'Select a backtest file from the left to view detailed analysis'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
