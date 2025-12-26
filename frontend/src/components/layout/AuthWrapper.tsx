'use client';

import { usePathname } from 'next/navigation';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { AIChat } from '@/components/chat/AIChat';
import { AuthProvider } from '@/lib/auth';

interface AuthWrapperProps {
    children: React.ReactNode;
}

export function AuthWrapper({ children }: AuthWrapperProps) {
    const pathname = usePathname();

    // 登入頁面使用簡化布局
    const isLoginPage = pathname === '/login';

    if (isLoginPage) {
        return (
            <AuthProvider>
                {children}
            </AuthProvider>
        );
    }

    // 其他頁面使用完整布局
    return (
        <AuthProvider>
            <Header />
            <div className="flex">
                <Sidebar />
                <main className="flex-1 ml-64 min-h-[calc(100vh-4rem)] p-6">
                    {children}
                </main>
            </div>
            <AIChat />
        </AuthProvider>
    );
}
