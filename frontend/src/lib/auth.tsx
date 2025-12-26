'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

// 使用相對路徑，透過 Next.js rewrites 代理到後端

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    userId: string | null;
    displayName: string | null;
    token: string | null;
    login: (token: string, userId: string, displayName: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
    isAuthenticated: false,
    isLoading: true,
    userId: null,
    displayName: null,
    token: null,
    login: () => { },
    logout: () => { },
});

export function useAuth() {
    return useContext(AuthContext);
}

interface AuthProviderProps {
    children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
    const router = useRouter();
    const pathname = usePathname();
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [userId, setUserId] = useState<string | null>(null);
    const [displayName, setDisplayName] = useState<string | null>(null);
    const [token, setToken] = useState<string | null>(null);

    // 不需要認證的路徑
    const publicPaths = ['/login'];

    useEffect(() => {
        const checkAuth = async () => {
            const storedToken = localStorage.getItem('auth_token');
            const storedUserId = localStorage.getItem('user_id');
            const storedDisplayName = localStorage.getItem('display_name');

            if (!storedToken) {
                setIsLoading(false);
                if (!publicPaths.includes(pathname)) {
                    router.replace('/login');
                }
                return;
            }

            // 驗證 token
            try {
                const res = await fetch(`/api/auth/verify`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${storedToken}`,
                    },
                });
                const data = await res.json();

                if (data.valid) {
                    setIsAuthenticated(true);
                    setUserId(storedUserId);
                    setDisplayName(storedDisplayName);
                    setToken(storedToken);

                    // 如果在登入頁，跳轉到首頁
                    if (pathname === '/login') {
                        router.replace('/');
                    }
                } else {
                    // Token 無效
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_id');
                    localStorage.removeItem('display_name');
                    if (!publicPaths.includes(pathname)) {
                        router.replace('/login');
                    }
                }
            } catch (e) {
                console.error('Auth check failed:', e);
                if (!publicPaths.includes(pathname)) {
                    router.replace('/login');
                }
            }

            setIsLoading(false);
        };

        checkAuth();
    }, [pathname, router]);

    const login = (newToken: string, newUserId: string, newDisplayName: string) => {
        localStorage.setItem('auth_token', newToken);
        localStorage.setItem('user_id', newUserId);
        localStorage.setItem('display_name', newDisplayName);
        setToken(newToken);
        setUserId(newUserId);
        setDisplayName(newDisplayName);
        setIsAuthenticated(true);
    };

    const logout = () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('display_name');
        setToken(null);
        setUserId(null);
        setDisplayName(null);
        setIsAuthenticated(false);
        router.replace('/login');
    };

    // 如果正在載入中，顯示載入畫面
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    // 如果是公開頁面，直接顯示
    if (publicPaths.includes(pathname)) {
        return (
            <AuthContext.Provider value={{ isAuthenticated, isLoading, userId, displayName, token, login, logout }}>
                {children}
            </AuthContext.Provider>
        );
    }

    // 如果未認證，不顯示內容（等待跳轉）
    if (!isAuthenticated) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    return (
        <AuthContext.Provider value={{ isAuthenticated, isLoading, userId, displayName, token, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}
