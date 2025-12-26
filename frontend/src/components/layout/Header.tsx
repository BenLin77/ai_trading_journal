'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { Button } from '@/components/ui/button';
import { Sun, Moon, RefreshCw, AlertCircle, CheckCircle, LogOut, User } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth';

export function Header() {
  const { theme, toggleTheme, language, toggleLanguage, isSyncing, setIsSyncing, setLastSyncTime } = useAppStore();
  const { displayName, logout } = useAuth();
  const queryClient = useQueryClient();
  const [syncStatus, setSyncStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });

  const syncMutation = useMutation({
    mutationFn: apiClient.syncIBKR,
    onMutate: () => {
      setIsSyncing(true);
      setSyncStatus({ type: null, message: '' });
    },
    onSuccess: (data) => {
      setLastSyncTime(new Date().toISOString());
      queryClient.invalidateQueries();
      setSyncStatus({
        type: 'success',
        message: language === 'zh' ? '同步成功！' : 'Sync successful!'
      });
      // 3秒後清除訊息
      setTimeout(() => setSyncStatus({ type: null, message: '' }), 3000);
    },
    onError: (error: Error) => {
      console.error('Sync failed:', error);
      setSyncStatus({
        type: 'error',
        message: language === 'zh'
          ? `同步失敗: ${error.message || '請稍後再試'}`
          : `Sync failed: ${error.message || 'Please try again later'}`
      });
      // 5秒後清除錯誤訊息
      setTimeout(() => setSyncStatus({ type: null, message: '' }), 5000);
    },
    onSettled: () => setIsSyncing(false),
  });

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Logo & Title */}
        <div className="flex items-center gap-3">
          {/* Logo Icon */}
          <img
            src="/icon.svg"
            alt="Logo"
            className="h-8 w-8"
          />
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            {t('app_title', language)}
          </h1>
          <span className="text-sm text-gray-500 dark:text-gray-400 hidden md:inline">
            {t('app_subtitle', language)}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Sync Status Message */}
          {syncStatus.type && (
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm ${syncStatus.type === 'success'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              }`}>
              {syncStatus.type === 'success'
                ? <CheckCircle className="h-4 w-4" />
                : <AlertCircle className="h-4 w-4" />}
              <span className="max-w-[200px] truncate">{syncStatus.message}</span>
            </div>
          )}

          {/* User Display */}
          {displayName && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gray-100 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300">
              <User className="h-4 w-4" />
              <span>{displayName}</span>
            </div>
          )}

          {/* Language Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleLanguage}
            title={language === 'zh' ? 'Switch to English' : '切換至中文'}
          >
            {language === 'zh' ? 'EN' : '中'}
          </Button>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={theme === 'dark' ? t('settings_light', language) : t('settings_dark', language)}
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          {/* Sync Button */}
          <Button
            variant="default"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={isSyncing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? t('status_syncing', language) : t('action_sync', language)}
          </Button>

          {/* Logout Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            title={language === 'zh' ? '登出' : 'Logout'}
            className="text-gray-500 hover:text-red-500"
          >
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
