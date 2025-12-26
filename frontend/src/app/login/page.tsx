'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff, Loader2, AlertCircle, LogIn } from 'lucide-react';

// 使用相對路徑，透過 Next.js rewrites 代理到後端

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [checkingAuth, setCheckingAuth] = useState(true);

    // 檢查是否已登入
    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('auth_token');
            if (token) {
                try {
                    const res = await fetch(`/api/auth/verify`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    });
                    const data = await res.json();
                    if (data.valid) {
                        router.replace('/');
                        return;
                    }
                } catch (e) {
                    // Token 無效，清除
                    localStorage.removeItem('auth_token');
                }
            }
            setCheckingAuth(false);
        };
        checkAuth();
    }, [router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const res = await fetch(`/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await res.json();

            if (data.success && data.access_token) {
                // 存儲 token
                localStorage.setItem('auth_token', data.access_token);
                localStorage.setItem('user_id', data.user_id);
                localStorage.setItem('display_name', data.display_name);

                // 跳轉到首頁
                router.replace('/');
            } else {
                setError(data.message || '登入失敗');
            }
        } catch (err) {
            setError('網路錯誤，請稍後再試');
        } finally {
            setLoading(false);
        }
    };

    if (checkingAuth) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
            <div className="w-full max-w-md px-4">
                <Card className="border-gray-700 bg-gray-800/50 backdrop-blur-sm">
                    <CardHeader className="text-center pb-2">
                        <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                            <LogIn className="h-8 w-8 text-white" />
                        </div>
                        <CardTitle className="text-2xl font-bold text-white">
                            AI Trading Journal
                        </CardTitle>
                        <p className="text-gray-400 mt-2">
                            登入以繼續
                        </p>
                    </CardHeader>

                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {/* 用戶名 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    用戶名
                                </label>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="請輸入用戶名"
                                    className="w-full px-4 py-3 rounded-lg bg-gray-700 border border-gray-600 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    autoComplete="username"
                                    autoFocus
                                />
                            </div>

                            {/* 密碼 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    密碼
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="請輸入密碼"
                                        className="w-full px-4 py-3 pr-12 rounded-lg bg-gray-700 border border-gray-600 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        required
                                        autoComplete="current-password"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                                    >
                                        {showPassword ? (
                                            <EyeOff className="h-5 w-5" />
                                        ) : (
                                            <Eye className="h-5 w-5" />
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* 錯誤訊息 */}
                            {error && (
                                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
                                    <AlertCircle className="h-5 w-5 flex-shrink-0" />
                                    <span className="text-sm">{error}</span>
                                </div>
                            )}

                            {/* 登入按鈕 */}
                            <Button
                                type="submit"
                                disabled={loading || !username || !password}
                                className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-medium rounded-lg"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                        登入中...
                                    </>
                                ) : (
                                    '登入'
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <p className="text-center text-gray-500 text-sm mt-6">
                    © 2025 AI Trading Journal
                </p>
            </div>
        </div>
    );
}
