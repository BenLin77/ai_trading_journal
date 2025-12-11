'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Loader2, Settings as SettingsIcon, Globe, Moon, Sun, RefreshCw, Trash2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

export default function SettingsPage() {
  const { language, setLanguage, theme, setTheme } = useAppStore();
  const [recalcMessage, setRecalcMessage] = useState<string | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: apiClient.getSettings,
  });

  const recalcMutation = useMutation({
    mutationFn: apiClient.recalculatePnL,
    onSuccess: () => {
      setRecalcMessage(language === 'zh' ? '盈虧重新計算完成！' : 'P&L recalculated successfully!');
      setTimeout(() => setRecalcMessage(null), 3000);
    },
    onError: (error) => {
      setRecalcMessage(language === 'zh' ? `錯誤: ${error}` : `Error: ${error}`);
    },
  });

  const clearMutation = useMutation({
    mutationFn: apiClient.clearDatabase,
    onSuccess: () => {
      setClearConfirm(false);
      setRecalcMessage(language === 'zh' ? '資料庫已清空！' : 'Database cleared!');
      setTimeout(() => setRecalcMessage(null), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <SettingsIcon className="h-6 w-6" />
          {language === 'zh' ? '系統設定' : 'Settings'}
        </h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? '管理應用程式偏好設定和維護' : 'Manage application preferences and maintenance'}
        </p>
      </div>

      {/* 狀態提示 */}
      {recalcMessage && (
        <div className={cn(
          'p-4 rounded-lg flex items-center gap-3',
          recalcMessage.includes('錯誤') || recalcMessage.includes('Error')
            ? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
            : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200'
        )}>
          <CheckCircle className="h-5 w-5" />
          {recalcMessage}
        </div>
      )}

      {/* 外觀設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            {language === 'zh' ? '外觀設定' : 'Appearance'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 語言 */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 block">
              {language === 'zh' ? '語言 / Language' : 'Language / 語言'}
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => setLanguage('zh')}
                className={cn(
                  'flex-1 px-4 py-3 rounded-lg text-center transition-colors',
                  language === 'zh'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
              >
                🇹🇼 繁體中文
              </button>
              <button
                onClick={() => setLanguage('en')}
                className={cn(
                  'flex-1 px-4 py-3 rounded-lg text-center transition-colors',
                  language === 'en'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
              >
                🇺🇸 English
              </button>
            </div>
          </div>

          {/* 主題 */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 block">
              {language === 'zh' ? '主題' : 'Theme'}
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => setTheme('dark')}
                className={cn(
                  'flex-1 px-4 py-3 rounded-lg text-center transition-colors flex items-center justify-center gap-2',
                  theme === 'dark'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
              >
                <Moon className="h-4 w-4" />
                {language === 'zh' ? '深色' : 'Dark'}
              </button>
              <button
                onClick={() => setTheme('light')}
                className={cn(
                  'flex-1 px-4 py-3 rounded-lg text-center transition-colors flex items-center justify-center gap-2',
                  theme === 'light'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
              >
                <Sun className="h-4 w-4" />
                {language === 'zh' ? '淺色' : 'Light'}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 連線狀態 */}
      <Card>
        <CardHeader>
          <CardTitle>{language === 'zh' ? '🔌 連線狀態' : '🔌 Connection Status'}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <span className="text-lg">📊</span>
              <span>IBKR Flex Query</span>
            </div>
            {settings?.ibkr_configured ? (
              <span className="flex items-center gap-1 text-emerald-600">
                <CheckCircle className="h-4 w-4" />
                {language === 'zh' ? '已設定' : 'Configured'}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-gray-500">
                <XCircle className="h-4 w-4" />
                {language === 'zh' ? '未設定' : 'Not Configured'}
              </span>
            )}
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3">
              <span className="text-lg">🤖</span>
              <span>AI (Gemini)</span>
            </div>
            {settings?.ai_configured ? (
              <span className="flex items-center gap-1 text-emerald-600">
                <CheckCircle className="h-4 w-4" />
                {language === 'zh' ? '已設定' : 'Configured'}
              </span>
            ) : (
              <span className="flex items-center gap-1 text-gray-500">
                <XCircle className="h-4 w-4" />
                {language === 'zh' ? '未設定' : 'Not Configured'}
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 系統維護 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            {language === 'zh' ? '系統維護' : 'System Maintenance'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div>
              <p className="font-medium">{language === 'zh' ? '重新計算盈虧' : 'Recalculate P&L'}</p>
              <p className="text-sm text-gray-500">
                {language === 'zh' ? '根據交易紀錄重新計算所有盈虧數據' : 'Recalculate all P&L based on trade records'}
              </p>
            </div>
            <Button
              onClick={() => recalcMutation.mutate()}
              disabled={recalcMutation.isPending}
              variant="secondary"
            >
              {recalcMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              {language === 'zh' ? '執行' : 'Run'}
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div>
              <p className="font-medium text-red-800 dark:text-red-200 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {language === 'zh' ? '清空資料庫' : 'Clear Database'}
              </p>
              <p className="text-sm text-red-600 dark:text-red-300">
                {language === 'zh' ? '⚠️ 此操作無法復原，將刪除所有交易紀錄' : '⚠️ This action cannot be undone, all trade records will be deleted'}
              </p>
            </div>
            {clearConfirm ? (
              <div className="flex gap-2">
                <Button
                  onClick={() => clearMutation.mutate()}
                  disabled={clearMutation.isPending}
                  variant="destructive"
                  size="sm"
                >
                  {clearMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : language === 'zh' ? '確認刪除' : 'Confirm'}
                </Button>
                <Button
                  onClick={() => setClearConfirm(false)}
                  variant="secondary"
                  size="sm"
                >
                  {language === 'zh' ? '取消' : 'Cancel'}
                </Button>
              </div>
            ) : (
              <Button
                onClick={() => setClearConfirm(true)}
                variant="destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {language === 'zh' ? '清空' : 'Clear'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 環境變數說明 */}
      <Card>
        <CardHeader>
          <CardTitle>{language === 'zh' ? '📝 環境變數設定' : '📝 Environment Variables'}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm overflow-x-auto">
            <p className="text-gray-500"># .env</p>
            <p className="mt-2"><span className="text-emerald-400">GEMINI_API_KEY</span>=your_api_key</p>
            <p><span className="text-emerald-400">IBKR_FLEX_TOKEN</span>=your_flex_token</p>
            <p><span className="text-emerald-400">IBKR_HISTORY_QUERY_ID</span>=your_query_id</p>
            <p><span className="text-emerald-400">IBKR_POSITIONS_QUERY_ID</span>=your_query_id</p>
          </div>
          <p className="text-sm text-gray-500 mt-3">
            {language === 'zh'
              ? '在專案根目錄創建 .env 檔案並填入上述變數'
              : 'Create a .env file in the project root with the above variables'}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
