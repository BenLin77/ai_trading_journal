'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient, GroupedSymbol, ReviewChartData } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, formatDateTime, cn, getPnLColor } from '@/lib/utils';
import { Loader2, Send, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';

export default function ReviewPage() {
  const { language } = useAppStore();
  const [selectedUnderlying, setSelectedUnderlying] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);

  // 獲取按 underlying 分組的標的清單
  const { data: groupedSymbols, isLoading: symbolsLoading } = useQuery({
    queryKey: ['grouped-symbols'],
    queryFn: apiClient.getGroupedSymbols,
  });

  // 獲取選中標的的 K 線圖數據
  const { data: chartData, isLoading: chartLoading, error: chartError } = useQuery({
    queryKey: ['review-chart', selectedUnderlying],
    queryFn: () => apiClient.getReviewChartData(selectedUnderlying!, '1y'),
    enabled: !!selectedUnderlying,
  });

  // AI 聊天，傳送 K 線圖和買賣點資訊
  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      // 如果有圖表數據，將其加入對話上下文
      let contextMessage = message;
      if (chartData) {
        const summary = chartData.summary;
        const tradesInfo = chartData.trades.map(t =>
          `${t.datetime}: ${t.action} ${t.quantity} ${t.is_option ? `選擇權(${t.option_type} $${t.strike})` : '股票'} @ $${t.price}`
        ).join('\n');

        contextMessage = `
我正在檢討 ${selectedUnderlying} 的交易，以下是相關數據：

📊 K 線圖摘要：
- 當前價格: $${summary.current_price}
- 總交易次數: ${summary.total_trades} (股票: ${summary.stock_trades}, 選擇權: ${summary.option_trades})
- 買入 ${summary.buy_count} 次, 平均價格: $${summary.avg_buy_price}
- 賣出 ${summary.sell_count} 次, 平均價格: $${summary.avg_sell_price}
- 已實現盈虧: $${summary.total_realized_pnl}

📋 交易記錄：
${tradesInfo}

我的問題: ${message}

請根據上述買賣點和 K 線走勢，分析我的交易時機是否正確，並給出具體的改進建議。`;
      }

      return apiClient.aiChat(contextMessage, selectedUnderlying || undefined);
    },
    onSuccess: (data) => {
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    },
    onError: () => {
      setChatMessages(prev => [...prev, { role: 'assistant', content: '抱歉，發生錯誤，請稍後再試。' }]);
    },
  });

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;
    setChatMessages(prev => [...prev, { role: 'user', content: chatInput }]);
    chatMutation.mutate(chatInput);
    setChatInput('');
  };

  const handleSelectUnderlying = (underlying: string) => {
    setSelectedUnderlying(underlying);
    setChatMessages([]); // 清除之前的對話
  };

  if (symbolsLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('nav_review', language)}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Symbol List - 按 underlying 分組 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {language === 'zh' ? '選擇標的' : 'Select Symbol'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[60vh] overflow-y-auto">
              {groupedSymbols?.map((group) => (
                <button
                  key={group.underlying}
                  onClick={() => handleSelectUnderlying(group.underlying)}
                  className={cn(
                    'w-full text-left px-3 py-3 rounded-lg transition-colors border',
                    selectedUnderlying === group.underlying
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-700'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800 border-transparent'
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold">{group.underlying}</span>
                    <span className={cn('text-sm font-medium', getPnLColor(group.total_pnl))}>
                      {formatCurrency(group.total_pnl, true)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3 text-emerald-500" />
                      {group.stock_trades} 股票
                    </span>
                    {group.option_trades > 0 && (
                      <span className="flex items-center gap-1">
                        <TrendingDown className="h-3 w-3 text-blue-500" />
                        {group.option_trades} 選擇權
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* K 線圖和交易明細 */}
        <div className="lg:col-span-3 space-y-6">
          {selectedUnderlying ? (
            <>
              {/* K 線圖 */}
              <Card>
                <CardHeader>
                  <CardTitle>
                    {selectedUnderlying} {language === 'zh' ? 'K 線圖與買賣點' : 'Price Chart with Trades'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {chartLoading ? (
                    <div className="flex items-center justify-center h-64">
                      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                      <span className="ml-2">{language === 'zh' ? '下載 K 線數據中...' : 'Loading chart data...'}</span>
                    </div>
                  ) : chartError ? (
                    <div className="flex items-center justify-center h-64 text-red-500">
                      {language === 'zh' ? '無法載入圖表數據' : 'Failed to load chart data'}
                    </div>
                  ) : chartData ? (
                    <div className="space-y-4">
                      {/* 摘要統計 */}
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500">{language === 'zh' ? '現價' : 'Current'}</p>
                          <p className="text-lg font-bold">${chartData.summary.current_price}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500">{language === 'zh' ? '總交易' : 'Trades'}</p>
                          <p className="text-lg font-bold">{chartData.summary.total_trades}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500">{language === 'zh' ? '平均買價' : 'Avg Buy'}</p>
                          <p className="text-lg font-bold text-emerald-500">${chartData.summary.avg_buy_price}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500">{language === 'zh' ? '平均賣價' : 'Avg Sell'}</p>
                          <p className="text-lg font-bold text-red-500">${chartData.summary.avg_sell_price}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 text-center">
                          <p className="text-xs text-gray-500">{language === 'zh' ? '已實現盈虧' : 'Realized'}</p>
                          <p className={cn('text-lg font-bold', getPnLColor(chartData.summary.total_realized_pnl))}>
                            {formatCurrency(chartData.summary.total_realized_pnl, true)}
                          </p>
                        </div>
                      </div>

                      {/* K 線圖 */}
                      <CandlestickChart
                        symbol={selectedUnderlying}
                        ohlcData={chartData.ohlc}
                        trades={chartData.trades}
                        height={450}
                      />
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              {/* 交易明細表 */}
              {chartData && (
                <Card>
                  <CardHeader>
                    <CardTitle>
                      {language === 'zh' ? '交易明細（股票+選擇權）' : 'Trade Details (Stock + Options)'}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 dark:border-gray-700">
                            <th className="text-left py-2 px-2">{language === 'zh' ? '日期' : 'Date'}</th>
                            <th className="text-left py-2 px-2">{language === 'zh' ? '標的' : 'Symbol'}</th>
                            <th className="text-left py-2 px-2">{language === 'zh' ? '類型' : 'Type'}</th>
                            <th className="text-left py-2 px-2">{language === 'zh' ? '動作' : 'Action'}</th>
                            <th className="text-right py-2 px-2">{language === 'zh' ? '數量' : 'Qty'}</th>
                            <th className="text-right py-2 px-2">{language === 'zh' ? '價格' : 'Price'}</th>
                            <th className="text-right py-2 px-2">{language === 'zh' ? '盈虧' : 'P&L'}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {chartData.trades.map((trade, idx) => (
                            <tr key={idx} className="border-b border-gray-100 dark:border-gray-800">
                              <td className="py-2 px-2 text-gray-500">{trade.date}</td>
                              <td className="py-2 px-2 font-medium">{trade.symbol}</td>
                              <td className="py-2 px-2">
                                <span className={cn(
                                  'px-2 py-0.5 rounded text-xs',
                                  trade.is_option
                                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                    : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                                )}>
                                  {trade.is_option ? `${trade.option_type} $${trade.strike}` : '股票'}
                                </span>
                              </td>
                              <td className="py-2 px-2">
                                <span className={cn(
                                  'px-2 py-0.5 rounded text-xs',
                                  trade.action.toUpperCase().includes('BUY')
                                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                                    : 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                                )}>
                                  {trade.action}
                                </span>
                              </td>
                              <td className="py-2 px-2 text-right">{trade.quantity}</td>
                              <td className="py-2 px-2 text-right">{formatCurrency(trade.price)}</td>
                              <td className={cn('py-2 px-2 text-right font-medium', getPnLColor(trade.realized_pnl))}>
                                {formatCurrency(trade.realized_pnl, true)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* AI 交易檢討 */}
              <Card>
                <CardHeader>
                  <CardTitle>
                    🤖 {language === 'zh' ? 'AI 交易檢討' : 'AI Trade Review'}
                    {selectedUnderlying && <span className="text-blue-500 ml-2">- {selectedUnderlying}</span>}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* 快捷問題按鈕 */}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const question = '分析我的買賣時機，哪些是好的決定，哪些需要改進？';
                          setChatMessages(prev => [...prev, { role: 'user', content: question }]);
                          chatMutation.mutate(question);
                        }}
                        disabled={chatMutation.isPending || !chartData}
                      >
                        分析買賣時機
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const question = '我是否有追高殺低的問題？如何改進？';
                          setChatMessages(prev => [...prev, { role: 'user', content: question }]);
                          chatMutation.mutate(question);
                        }}
                        disabled={chatMutation.isPending || !chartData}
                      >
                        檢查追高殺低
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const question = '根據目前的技術面，我應該加碼、減碼還是持有？';
                          setChatMessages(prev => [...prev, { role: 'user', content: question }]);
                          chatMutation.mutate(question);
                        }}
                        disabled={chatMutation.isPending || !chartData}
                      >
                        給我操作建議
                      </Button>
                    </div>

                    {/* 對話訊息 */}
                    <div className="h-64 overflow-y-auto space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                      {chatMessages.length === 0 ? (
                        <p className="text-gray-500 text-center">
                          {language === 'zh'
                            ? '選擇一個標的，AI 會分析你的買賣點和 K 線走勢...'
                            : 'Select a symbol and AI will analyze your trades...'}
                        </p>
                      ) : (
                        chatMessages.map((msg, idx) => (
                          <div
                            key={idx}
                            className={cn(
                              'p-3 rounded-lg max-w-[85%]',
                              msg.role === 'user'
                                ? 'bg-blue-600 text-white ml-auto whitespace-pre-wrap'
                                : 'bg-white dark:bg-gray-700'
                            )}
                          >
                            {msg.role === 'user' ? (
                              msg.content
                            ) : (
                              <MarkdownRenderer content={msg.content} />
                            )}
                          </div>
                        ))
                      )}
                      {chatMutation.isPending && (
                        <div className="flex items-center gap-2 text-gray-500">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {language === 'zh' ? '分析中...' : 'Analyzing...'}
                        </div>
                      )}
                    </div>

                    {/* 輸入框 */}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder={language === 'zh' ? '輸入問題，AI 會根據 K 線和買賣點分析...' : 'Ask about your trades...'}
                        className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        disabled={!chartData}
                      />
                      <Button onClick={handleSendMessage} disabled={chatMutation.isPending || !chartData}>
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center h-96">
                <BarChart3 className="h-16 w-16 text-gray-300 mb-4" />
                <p className="text-gray-500 text-lg">
                  {language === 'zh' ? '請選擇一個標的開始交易檢討' : 'Select a symbol to start review'}
                </p>
                <p className="text-gray-400 text-sm mt-2">
                  {language === 'zh'
                    ? '系統會自動下載 K 線數據，並顯示你的買賣點'
                    : 'Chart data will be downloaded automatically with your trade points'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
