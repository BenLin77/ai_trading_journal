'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  Loader2, Settings as SettingsIcon, Globe, Moon, Sun, RefreshCw, Trash2,
  CheckCircle, XCircle, AlertTriangle, Key, Eye, EyeOff, Save, TestTube, Send, Clock,
  Lock, Shield
} from 'lucide-react';

interface ConfigStatus {
  ibkr: {
    configured: boolean;
    token_set: boolean;
    token_preview: string;
    history_query_id: string;
    positions_query_id: string;
  };
  ai: {
    configured: boolean;
    provider: string;
    gemini_set: boolean;
    deepseek_set: boolean;
    openai_set: boolean;
  };
  telegram?: {
    configured: boolean;
    token_set: boolean;
    token_preview?: string;
    chat_id: string;
    daily_time: string;
    enabled: boolean;
  };
  data_source?: {
    current: 'QUERY' | 'GATEWAY';
    available: string[];
    gateway_host: string;
    gateway_port: string;
  };
}

interface ValidationResult {
  success: boolean;
  message: string;
  details?: {
    available_models?: string[];
    reference_code?: string;
    query_id?: string;
    raw_response?: string;
  };
}

export default function SettingsPage() {
  const { language, setLanguage, theme, setTheme } = useAppStore();
  const queryClient = useQueryClient();

  // 表單狀態 - IBKR
  const [ibkrToken, setIbkrToken] = useState('');
  const [ibkrHistoryId, setIbkrHistoryId] = useState('');
  const [ibkrPositionsId, setIbkrPositionsId] = useState('');

  // 表單狀態 - AI
  const [geminiKey, setGeminiKey] = useState('');
  const [deepseekKey, setDeepseekKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [aiProvider, setAiProvider] = useState('gemini');

  // 表單狀態 - Telegram
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [telegramTime, setTelegramTime] = useState('08:00');
  const [telegramEnabled, setTelegramEnabled] = useState(false);

  // UI 狀態
  const [showIbkrToken, setShowIbkrToken] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showDeepseekKey, setShowDeepseekKey] = useState(false);
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);
  const [showTelegramToken, setShowTelegramToken] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);

  // 驗證結果
  const [ibkrValidation, setIbkrValidation] = useState<ValidationResult | null>(null);
  const [aiValidation, setAiValidation] = useState<ValidationResult | null>(null);

  // 資料來源狀態
  const [dataSource, setDataSource] = useState<'QUERY' | 'GATEWAY'>('QUERY');
  const [isTestingGateway, setIsTestingGateway] = useState(false);

  // 取得設定狀態
  const { data: configStatus, isLoading } = useQuery<ConfigStatus>({
    queryKey: ['config-status'],
    queryFn: async () => {
      const response = await fetch('/api/config/status');
      return response.json();
    },
  });

  // 初始化表單
  useEffect(() => {
    if (configStatus) {
      setIbkrHistoryId(configStatus.ibkr.history_query_id || '');
      setIbkrPositionsId(configStatus.ibkr.positions_query_id || '');
      setAiProvider(configStatus.ai.provider || 'gemini');

      if (configStatus.telegram) {
        // 如果 API 有設定 chat_id，設定到表單（只在初始化時設定）
        if (configStatus.telegram.chat_id && !telegramChatId) {
          setTelegramChatId(configStatus.telegram.chat_id);
        }
        setTelegramTime(configStatus.telegram.daily_time || '08:00');
        setTelegramEnabled(configStatus.telegram.enabled || false);
      }

      if (configStatus.data_source) {
        setDataSource(configStatus.data_source.current || 'QUERY');
      }
    }
  }, [configStatus]);

  // 切換資料來源
  const switchDataSourceMutation = useMutation({
    mutationFn: async (source: 'QUERY' | 'GATEWAY') => {
      const response = await fetch('/api/data-source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        setDataSource(data.current);
        setMessage({ type: 'success', text: data.message });
        queryClient.invalidateQueries({ queryKey: ['config-status'] });
      } else {
        setMessage({ type: 'error', text: data.message || '切換失敗' });
      }
      setTimeout(() => setMessage(null), 3000);
    },
    onError: (error) => {
      setMessage({ type: 'error', text: `切換失敗: ${error}` });
    },
  });

  // 驗證 IBKR
  const validateIbkrMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/config/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_type: 'ibkr',
          token: ibkrToken || undefined,
          query_id: ibkrHistoryId || undefined,
        }),
      });
      return response.json();
    },
    onSuccess: (data) => {
      setIbkrValidation(data);
    },
  });

  // 驗證 AI
  const validateAiMutation = useMutation({
    mutationFn: async () => {
      const token = aiProvider === 'gemini' ? geminiKey :
        aiProvider === 'deepseek' ? deepseekKey : openaiKey;
      const response = await fetch('/api/config/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config_type: aiProvider,
          token: token || undefined,
        }),
      });
      return response.json();
    },
    onSuccess: (data) => {
      setAiValidation(data);
    },
  });

  // 儲存設定
  const saveMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ibkr_flex_token: ibkrToken || undefined,
          ibkr_history_query_id: ibkrHistoryId || undefined,
          ibkr_positions_query_id: ibkrPositionsId || undefined,
          gemini_api_key: geminiKey || undefined,
          deepseek_api_key: deepseekKey || undefined,
          openai_api_key: openaiKey || undefined,
          ai_provider: aiProvider,
          telegram_bot_token: telegramToken || undefined,
          telegram_chat_id: telegramChatId || undefined,
          telegram_daily_time: telegramTime,
          telegram_enabled: telegramEnabled,
        }),
      });
      return response.json();
    },
    onSuccess: (data) => {
      setMessage({ type: 'success', text: data.message || '設定已儲存' });
      queryClient.invalidateQueries({ queryKey: ['config-status'] });
      setTimeout(() => setMessage(null), 5000);
    },
    onError: (error) => {
      setMessage({ type: 'error', text: `儲存失敗: ${error}` });
    },
  });

  // 重新計算盈虧
  const recalcMutation = useMutation({
    mutationFn: apiClient.recalculatePnL,
    onSuccess: () => {
      setMessage({ type: 'success', text: language === 'zh' ? '盈虧重新計算完成！' : 'P&L recalculated!' });
      setTimeout(() => setMessage(null), 3000);
    },
  });

  // 清空資料庫
  const clearMutation = useMutation({
    mutationFn: apiClient.clearDatabase,
    onSuccess: () => {
      setClearConfirm(false);
      setMessage({ type: 'success', text: language === 'zh' ? '資料庫已清空！' : 'Database cleared!' });
      setTimeout(() => setMessage(null), 3000);
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
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <SettingsIcon className="h-6 w-6" />
          {language === 'zh' ? '系統設定' : 'Settings'}
        </h1>
        <p className="text-gray-500 mt-1">
          {language === 'zh' ? '設定 API 金鑰和系統偏好' : 'Configure API keys and system preferences'}
        </p>
      </div>

      {/* 狀態提示 */}
      {message && (
        <div className={cn(
          'p-4 rounded-lg flex items-center gap-3',
          message.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200' :
            message.type === 'success' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200' :
              'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
        )}>
          {message.type === 'success' ? <CheckCircle className="h-5 w-5" /> :
            message.type === 'error' ? <XCircle className="h-5 w-5" /> :
              <AlertTriangle className="h-5 w-5" />}
          {message.text}
        </div>
      )}

      {/* IBKR 設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            IBKR Flex Query {language === 'zh' ? '設定' : 'Configuration'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Token */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Flex Web Service Token
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={showIbkrToken ? 'text' : 'password'}
                  value={ibkrToken}
                  onChange={(e) => setIbkrToken(e.target.value)}
                  placeholder={configStatus?.ibkr.token_preview || 'Enter your IBKR Flex Token'}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowIbkrToken(!showIbkrToken)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                >
                  {showIbkrToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>

          {/* History Query ID */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              History Query ID ({language === 'zh' ? '交易記錄' : 'Trade History'})
            </label>
            <input
              type="text"
              value={ibkrHistoryId}
              onChange={(e) => setIbkrHistoryId(e.target.value)}
              placeholder="e.g., 1344117"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
            />
          </div>

          {/* Positions Query ID */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Positions Query ID ({language === 'zh' ? '持倉快照' : 'Positions Snapshot'})
            </label>
            <input
              type="text"
              value={ibkrPositionsId}
              onChange={(e) => setIbkrPositionsId(e.target.value)}
              placeholder="e.g., 1337233"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
            />
          </div>

          {/* 驗證結果 */}
          {ibkrValidation && (
            <div className={cn(
              'p-3 rounded-lg text-sm',
              ibkrValidation.success
                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200'
                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
            )}>
              <div className="flex items-center gap-2">
                {ibkrValidation.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {ibkrValidation.message}
              </div>
            </div>
          )}

          {/* 驗證按鈕 */}
          <div className="flex gap-2">
            <Button
              onClick={() => validateIbkrMutation.mutate()}
              disabled={validateIbkrMutation.isPending}
              variant="secondary"
            >
              {validateIbkrMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <TestTube className="h-4 w-4 mr-2" />
              )}
              {language === 'zh' ? '測試連線' : 'Test Connection'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 資料來源設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🔄 {language === 'zh' ? '資料來源設定' : 'Data Source Configuration'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-500">
            {language === 'zh'
              ? '選擇如何獲取持倉和交易數據。QUERY 模式透過 Flex Query API 取得歷史快照，GATEWAY 模式透過 IB Gateway 取得即時數據。'
              : 'Choose how to fetch positions and trades. QUERY mode uses Flex Query API for historical snapshots, GATEWAY mode uses IB Gateway for real-time data.'}
          </p>

          <div className="flex gap-3">
            <button
              onClick={() => switchDataSourceMutation.mutate('QUERY')}
              disabled={switchDataSourceMutation.isPending}
              className={cn(
                'flex-1 px-4 py-3 rounded-lg text-center transition-colors flex flex-col items-center gap-1',
                dataSource === 'QUERY'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
            >
              <span className="font-medium">📊 Flex Query</span>
              <span className="text-xs opacity-80">{language === 'zh' ? '歷史資料' : 'Historical'}</span>
            </button>
            <button
              onClick={() => switchDataSourceMutation.mutate('GATEWAY')}
              disabled={switchDataSourceMutation.isPending}
              className={cn(
                'flex-1 px-4 py-3 rounded-lg text-center transition-colors flex flex-col items-center gap-1',
                dataSource === 'GATEWAY'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
            >
              <span className="font-medium">⚡ IB Gateway</span>
              <span className="text-xs opacity-80">{language === 'zh' ? '即時連線' : 'Real-time'}</span>
            </button>
          </div>

          {configStatus?.data_source && (
            <div className="text-sm text-gray-500 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg">
              <div className="flex items-center justify-between">
                <span>{language === 'zh' ? '當前模式' : 'Current Mode'}:</span>
                <span className={cn(
                  'font-medium',
                  dataSource === 'GATEWAY' ? 'text-emerald-600' : 'text-blue-600'
                )}>
                  {dataSource}
                </span>
              </div>
              {dataSource === 'GATEWAY' && configStatus.data_source.gateway_host && (
                <div className="flex items-center justify-between mt-1">
                  <span>Gateway:</span>
                  <span className="font-mono text-xs">
                    {configStatus.data_source.gateway_host}:{configStatus.data_source.gateway_port}
                  </span>
                </div>
              )}
            </div>
          )}

          {dataSource === 'GATEWAY' && (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-sm text-amber-800 dark:text-amber-200">
              <AlertTriangle className="h-4 w-4 inline mr-2" />
              {language === 'zh'
                ? '請確保 IB Gateway 或 TWS 已在本地運行並允許 API 連接。'
                : 'Make sure IB Gateway or TWS is running locally and API connections are enabled.'}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI 設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🤖 AI {language === 'zh' ? '設定' : 'Configuration'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* AI Provider 選擇 */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              AI Provider
            </label>
            <div className="flex gap-2">
              {['gemini', 'deepseek', 'openai'].map((provider) => (
                <button
                  key={provider}
                  onClick={() => setAiProvider(provider)}
                  className={cn(
                    'flex-1 px-4 py-2 rounded-lg text-center transition-colors capitalize',
                    aiProvider === provider
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                  )}
                >
                  {provider === 'gemini' ? '🔷 Gemini' :
                    provider === 'deepseek' ? '🐋 DeepSeek' : '🟢 OpenAI'}
                </button>
              ))}
            </div>
          </div>

          {/* Gemini API Key */}
          {aiProvider === 'gemini' && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Gemini API Key
              </label>
              <div className="relative">
                <input
                  type={showGeminiKey ? 'text' : 'password'}
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder={configStatus?.ai.gemini_set ? '••••••••••••' : 'Enter your Gemini API Key'}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                >
                  {showGeminiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {language === 'zh' ? '從 Google AI Studio 取得' : 'Get from Google AI Studio'}:
                <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-500 ml-1">
                  aistudio.google.com
                </a>
              </p>
            </div>
          )}

          {/* DeepSeek API Key */}
          {aiProvider === 'deepseek' && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                DeepSeek API Key
              </label>
              <div className="relative">
                <input
                  type={showDeepseekKey ? 'text' : 'password'}
                  value={deepseekKey}
                  onChange={(e) => setDeepseekKey(e.target.value)}
                  placeholder={configStatus?.ai.deepseek_set ? '••••••••••••' : 'Enter your DeepSeek API Key'}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowDeepseekKey(!showDeepseekKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                >
                  {showDeepseekKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {language === 'zh' ? '從 DeepSeek 取得' : 'Get from DeepSeek'}:
                <a href="https://platform.deepseek.com/" target="_blank" rel="noopener noreferrer" className="text-blue-500 ml-1">
                  platform.deepseek.com
                </a>
              </p>
            </div>
          )}

          {/* OpenAI API Key */}
          {aiProvider === 'openai' && (
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                OpenAI API Key
              </label>
              <div className="relative">
                <input
                  type={showOpenaiKey ? 'text' : 'password'}
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={configStatus?.ai.openai_set ? '••••••••••••' : 'Enter your OpenAI API Key'}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowOpenaiKey(!showOpenaiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
                >
                  {showOpenaiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {language === 'zh' ? '從 OpenAI 取得' : 'Get from OpenAI'}:
                <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-500 ml-1">
                  platform.openai.com
                </a>
              </p>
            </div>
          )}

          {/* 驗證結果 */}
          {aiValidation && (
            <div className={cn(
              'p-3 rounded-lg text-sm',
              aiValidation.success
                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200'
                : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
            )}>
              <div className="flex items-center gap-2">
                {aiValidation.success ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {aiValidation.message}
              </div>
              {aiValidation.details?.available_models && aiValidation.details.available_models.length > 0 && (
                <p className="mt-1 text-xs opacity-80">
                  Models: {aiValidation.details.available_models.slice(0, 3).join(', ')}...
                </p>
              )}
            </div>
          )}

          {/* 驗證按鈕 */}
          <div className="flex gap-2">
            <Button
              onClick={() => validateAiMutation.mutate()}
              disabled={validateAiMutation.isPending}
              variant="secondary"
            >
              {validateAiMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <TestTube className="h-4 w-4 mr-2" />
              )}
              {language === 'zh' ? '測試連線' : 'Test Connection'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Telegram 設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Telegram {language === 'zh' ? '通知設定' : 'Notifications'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">

          <div className="flex items-center justify-between mb-4 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg">
            <div className="flex flex-col">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {language === 'zh' ? '啟用每日戰情報告' : 'Enable Daily Report'}
              </label>
              <span className="text-xs text-gray-500">
                {language === 'zh' ? '在指定時間自動發送分析報告' : 'Automatically send analysis reports at specified time'}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setTelegramEnabled(!telegramEnabled)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                telegramEnabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
              )}
            >
              <span className={cn(
                "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                telegramEnabled ? "translate-x-6" : "translate-x-1"
              )} />
            </button>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Bot Token
            </label>
            <div className="relative">
              <input
                type={showTelegramToken ? 'text' : 'password'}
                value={telegramToken}
                onChange={(e) => setTelegramToken(e.target.value)}
                placeholder={configStatus?.telegram?.token_preview || (configStatus?.telegram?.token_set ? '••••••••••••' : 'Enter Telegram Bot Token')}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowTelegramToken(!showTelegramToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500"
              >
                {showTelegramToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Chat ID
            </label>
            <input
              type="text"
              value={telegramChatId}
              onChange={(e) => setTelegramChatId(e.target.value)}
              placeholder={configStatus?.telegram?.chat_id ?
                `${configStatus.telegram.chat_id.slice(0, 4)}${'*'.repeat(Math.max(0, configStatus.telegram.chat_id.length - 4))}` :
                'Chat ID (e.g. 123456789)'}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
            />
            {configStatus?.telegram?.chat_id && !telegramChatId && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {language === 'zh' ? '已從設定讀取 (部分遮罩)' : 'Loaded from config (partially masked)'}
              </p>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block flex items-center gap-2">
              <Clock className="h-4 w-4" />
              {language === 'zh' ? '發送時間 (台灣時間)' : 'Send Time (Asia/Taipei)'}
            </label>
            <input
              type="time"
              value={telegramTime}
              onChange={(e) => setTelegramTime(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
            />
          </div>

          {/* 狀態提示 */}
          {configStatus?.telegram?.configured && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg text-sm text-emerald-800 dark:text-emerald-200 flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              {language === 'zh' ? 'Telegram 已設定完成。您可以直接測試發送，或輸入新的值來覆蓋設定。' : 'Telegram is configured. You can test or enter new values to override.'}
            </div>
          )}

          {/* 測試按鈕 */}
          <div className="flex gap-2 mt-4">
            <Button
              type="button"
              onClick={() => {
                // 如果使用者有輸入新值，使用新值；否則使用 'use_saved' 標記讓後端使用已儲存的值
                const useNewToken = telegramToken || undefined;
                const useNewChatId = telegramChatId || undefined;
                const useSaved = !telegramToken && !telegramChatId && configStatus?.telegram?.configured;

                fetch('/api/telegram/test', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    token: useNewToken,
                    chat_id: useNewChatId,
                    use_saved: useSaved
                  })
                }).then(res => res.json()).then(data => {
                  setMessage({ type: data.success ? 'success' : 'error', text: data.message });
                  setTimeout(() => setMessage(null), 5000);
                }).catch(err => {
                  setMessage({ type: 'error', text: '請求失敗: ' + err });
                  setTimeout(() => setMessage(null), 3000);
                });
              }}
              variant="secondary"
              disabled={(!telegramToken || !telegramChatId) && !configStatus?.telegram?.configured}
            >
              <Send className="h-4 w-4 mr-2" />
              {language === 'zh' ? '測試發送' : 'Test Send'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 儲存按鈕 */}
      <div className="flex justify-end">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          size="lg"
        >
          {saveMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          {language === 'zh' ? '儲存所有設定' : 'Save All Settings'}
        </Button>
      </div>

      {/* 帳戶安全 */}
      <PasswordChangeCard language={language} />

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
                繁體中文
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
                English
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
                {language === 'zh' ? '此操作無法復原，將刪除所有交易紀錄' : 'This action cannot be undone'}
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
                  {clearMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : language === 'zh' ? '確認' : 'Confirm'}
                </Button>
                <Button onClick={() => setClearConfirm(false)} variant="secondary" size="sm">
                  {language === 'zh' ? '取消' : 'Cancel'}
                </Button>
              </div>
            ) : (
              <Button onClick={() => setClearConfirm(true)} variant="destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                {language === 'zh' ? '清空' : 'Clear'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}


// 修改密碼卡片組件
function PasswordChangeCard({ language }: { language: 'zh' | 'en' }) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showOldPassword, setShowOldPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);



  const handleChangePassword = async () => {
    // 驗證
    if (!oldPassword || !newPassword || !confirmPassword) {
      setMessage({ type: 'error', text: language === 'zh' ? '請填寫所有欄位' : 'Please fill all fields' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: language === 'zh' ? '新密碼與確認密碼不一致' : 'New passwords do not match' });
      return;
    }

    if (newPassword.length < 6) {
      setMessage({ type: 'error', text: language === 'zh' ? '新密碼長度至少 6 個字元' : 'New password must be at least 6 characters' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setMessage({ type: 'success', text: language === 'zh' ? '密碼修改成功' : 'Password changed successfully' });
        setOldPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setMessage({ type: 'error', text: data.detail || data.message || (language === 'zh' ? '修改失敗' : 'Failed to change password') });
      }
    } catch (err) {
      setMessage({ type: 'error', text: language === 'zh' ? '網路錯誤' : 'Network error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          {language === 'zh' ? '帳戶安全' : 'Account Security'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 訊息提示 */}
        {message && (
          <div className={cn(
            'p-3 rounded-lg flex items-center gap-2 text-sm',
            message.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-200'
              : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
          )}>
            {message.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {message.text}
          </div>
        )}

        {/* 舊密碼 */}
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
            {language === 'zh' ? '目前密碼' : 'Current Password'}
          </label>
          <div className="relative">
            <input
              type={showOldPassword ? 'text' : 'password'}
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder={language === 'zh' ? '請輸入目前密碼' : 'Enter current password'}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
            />
            <button
              type="button"
              onClick={() => setShowOldPassword(!showOldPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showOldPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* 新密碼 */}
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
            {language === 'zh' ? '新密碼' : 'New Password'}
          </label>
          <div className="relative">
            <input
              type={showNewPassword ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={language === 'zh' ? '請輸入新密碼 (至少 6 個字元)' : 'Enter new password (min 6 characters)'}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
            />
            <button
              type="button"
              onClick={() => setShowNewPassword(!showNewPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* 確認新密碼 */}
        <div>
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
            {language === 'zh' ? '確認新密碼' : 'Confirm New Password'}
          </label>
          <div className="relative">
            <input
              type={showConfirmPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={language === 'zh' ? '再次輸入新密碼' : 'Re-enter new password'}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pr-10"
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* 修改按鈕 */}
        <Button
          onClick={handleChangePassword}
          disabled={isLoading || !oldPassword || !newPassword || !confirmPassword}
          className="w-full"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Lock className="h-4 w-4 mr-2" />
          )}
          {language === 'zh' ? '修改密碼' : 'Change Password'}
        </Button>
      </CardContent>
    </Card>
  );
}
