'use client';

import Link from 'next/link';
import { Home, ArrowLeft } from 'lucide-react';

export default function NotFound() {
    return (
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
            <div className="text-center max-w-md">
                {/* 404 圖示 */}
                <div className="mb-8">
                    <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 mb-4">
                        <span className="text-5xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                            404
                        </span>
                    </div>
                </div>

                {/* 標題和描述 */}
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    頁面不存在
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mb-8">
                    您要找的頁面可能已被移除、名稱已更改，或暫時無法使用。
                </p>

                {/* 操作按鈕 */}
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <Link
                        href="/"
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
                    >
                        <Home className="w-4 h-4" />
                        返回首頁
                    </Link>
                    <button
                        onClick={() => window.history.back()}
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-all duration-200"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        返回上一頁
                    </button>
                </div>
            </div>
        </div>
    );
}
