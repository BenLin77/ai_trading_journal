'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient, Trade } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, formatDateTime, cn, getPnLColor } from '@/lib/utils';
import { Loader2, Send } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

export default function ReviewPage() {
  const { language } = useAppStore();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);

  const { data: symbols, isLoading: symbolsLoading } = useQuery({
    queryKey: ['symbols'],
    queryFn: apiClient.getSymbols,
  });

  const { data: trades, isLoading: tradesLoading } = useQuery({
    queryKey: ['trades', selectedSymbol],
    queryFn: () => apiClient.getTrades({ symbol: selectedSymbol || undefined, limit: 50 }),
  });

  const chatMutation = useMutation({
    mutationFn: (message: string) => apiClient.aiChat(message, selectedSymbol || undefined),
    onSuccess: (data) => {
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    },
  });

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;
    setChatMessages(prev => [...prev, { role: 'user', content: chatInput }]);
    chatMutation.mutate(chatInput);
    setChatInput('');
  };

  const isLoading = symbolsLoading || tradesLoading;

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('nav_review', language)}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Symbol List */}
        <Card>
          <CardHeader>
            <CardTitle>{language === 'zh' ? '選擇標的' : 'Select Symbol'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              <button
                onClick={() => setSelectedSymbol(null)}
                className={cn(
                  'w-full text-left px-3 py-2 rounded-lg transition-colors',
                  selectedSymbol === null
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {language === 'zh' ? '全部標的' : 'All Symbols'}
              </button>
              {symbols?.map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => setSelectedSymbol(symbol)}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded-lg transition-colors',
                    selectedSymbol === symbol
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  )}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Trade List */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              {selectedSymbol
                ? `${selectedSymbol} ${language === 'zh' ? '交易記錄' : 'Trades'}`
                : language === 'zh' ? '所有交易記錄' : 'All Trades'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-2 px-2">{language === 'zh' ? '日期' : 'Date'}</th>
                    <th className="text-left py-2 px-2">{language === 'zh' ? '標的' : 'Symbol'}</th>
                    <th className="text-left py-2 px-2">{language === 'zh' ? '動作' : 'Action'}</th>
                    <th className="text-right py-2 px-2">{language === 'zh' ? '數量' : 'Qty'}</th>
                    <th className="text-right py-2 px-2">{language === 'zh' ? '價格' : 'Price'}</th>
                    <th className="text-right py-2 px-2">{language === 'zh' ? '盈虧' : 'P&L'}</th>
                  </tr>
                </thead>
                <tbody>
                  {trades?.map((trade) => (
                    <tr key={trade.id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-2 px-2 text-gray-500">{formatDateTime(trade.datetime)}</td>
                      <td className="py-2 px-2 font-medium">{trade.symbol}</td>
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
      </div>

      {/* AI Chat */}
      <Card>
        <CardHeader>
          <CardTitle>{language === 'zh' ? 'AI 交易檢討' : 'AI Trade Review'}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Messages */}
            <div className="h-64 overflow-y-auto space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
              {chatMessages.length === 0 ? (
                <p className="text-gray-500 text-center">
                  {language === 'zh' ? '詢問 AI 關於你的交易...' : 'Ask AI about your trades...'}
                </p>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      'p-3 rounded-lg max-w-[80%]',
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white ml-auto'
                        : 'bg-white dark:bg-gray-700'
                    )}
                  >
                    {msg.content}
                  </div>
                ))
              )}
              {chatMutation.isPending && (
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {language === 'zh' ? '思考中...' : 'Thinking...'}
                </div>
              )}
            </div>

            {/* Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder={language === 'zh' ? '輸入問題...' : 'Type your question...'}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Button onClick={handleSendMessage} disabled={chatMutation.isPending}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
