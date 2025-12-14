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
  CheckCircle, XCircle, AlertTriangle, Key, Eye, EyeOff, Save, TestTube, Send, Clock
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
    chat_id: string;
    daily_time: string;
    enabled: boolean;
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

  // 取得設定狀態
  const { data: configStatus, isLoading } = useQuery<ConfigStatus>({
    queryKey: ['config-status'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/config/status');
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
        setTelegramChatId(configStatus.telegram.chat_id || '');
        setTelegramTime(configStatus.telegram.daily_time || '08:00');
        setTelegramEnabled(configStatus.telegram.enabled || false);
      }
    }
  }, [configStatus]);

  // 驗證 IBKR
  const validateIbkrMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('http://localhost:8000/api/config/validate', {
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
      const response = await fetch('http://localhost:8000/api/config/validate', {
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
      const response = await fetch('http://localhost:8000/api/config/save', {
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
                placeholder={configStatus?.telegram?.token_set ? '••••••••••••' : 'Enter Telegram Bot Token'}
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
              placeholder="Chat ID (e.g. 123456789)"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
            />
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

          {/* 測試按鈕 */}
          <div className="flex gap-2 mt-4">
            <Button
              type="button"
              onClick={() => {
                fetch('http://localhost:8000/api/telegram/test', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ token: telegramToken, chat_id: telegramChatId })
                }).then(res => res.json()).then(data => {
                  setMessage({ type: data.success ? 'success' : 'error', text: data.message });
                  setTimeout(() => setMessage(null), 3000);
                }).catch(err => {
                  setMessage({ type: 'error', text: '請求失敗: ' + err });
                  setTimeout(() => setMessage(null), 3000);
                });
              }}
              variant="secondary"
              disabled={!telegramToken || !telegramChatId}
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
