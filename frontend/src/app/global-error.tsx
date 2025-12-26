'use client';

import { Inter } from 'next/font/google';

const inter = Inter({
    variable: '--font-inter',
    subsets: ['latin'],
});

interface GlobalErrorProps {
    error: Error & { digest?: string };
    reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
    return (
        <html lang="en">
            <body className={`${inter.variable} font-sans antialiased bg-gray-950 text-gray-100`}>
                <div className="min-h-screen flex items-center justify-center p-4">
                    <div className="text-center max-w-md">
                        {/* 嚴重錯誤圖示 */}
                        <div className="mb-8">
                            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-red-500/20 mb-4">
                                <svg
                                    className="w-12 h-12 text-red-500"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    strokeWidth={2}
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                    />
                                </svg>
                            </div>
                        </div>

                        {/* 標題和描述 */}
                        <h1 className="text-2xl font-bold mb-2">系統錯誤</h1>
                        <p className="text-gray-400 mb-4">
                            系統遇到了嚴重錯誤，請重新載入頁面或聯繫管理員。
                        </p>

                        {/* 錯誤追蹤 ID */}
                        {error.digest && (
                            <p className="text-xs text-gray-500 mb-6 font-mono">
                                錯誤代碼：{error.digest}
                            </p>
                        )}

                        {/* 重試按鈕 */}
                        <button
                            onClick={reset}
                            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all duration-200"
                        >
                            重新載入
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
