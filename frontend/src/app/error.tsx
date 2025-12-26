'use client';

import { useEffect } from 'react';
import { RefreshCw, Home, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

interface ErrorProps {
    error: Error & { digest?: string };
    reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
    useEffect(() => {
        // 在生產環境中，這裡可以發送錯誤到 Sentry 等監控服務
        // 注意：不要在 console 中輸出敏感的錯誤詳情
        if (process.env.NODE_ENV === 'production') {
            // TODO: 發送到 Sentry
            // Sentry.captureException(error);
        }
    }, [error]);

    return (
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
            <div className="text-center max-w-md">
                {/* 錯誤圖示 */}
                <div className="mb-8">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br from-red-500/20 to-orange-500/20 mb-4">
                        <AlertTriangle className="w-12 h-12 text-red-500" />
                    </div>
                </div>

                {/* 標題和描述 */}
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    發生錯誤
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                    抱歉，處理您的請求時發生了錯誤。請稍後再試。
                </p>

                {/* 錯誤追蹤 ID（不顯示敏感詳情） */}
                {error.digest && (
                    <p className="text-xs text-gray-500 dark:text-gray-500 mb-6 font-mono">
                        錯誤代碼：{error.digest}
                    </p>
                )}

                {/* 操作按鈕 */}
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                        onClick={reset}
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
                    >
                        <RefreshCw className="w-4 h-4" />
                        重試
                    </button>
                    <Link
                        href="/"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-all duration-200"
                    >
                        <Home className="w-4 h-4" />
                        返回首頁
                    </Link>
                </div>
            </div>
        </div>
    );
}
