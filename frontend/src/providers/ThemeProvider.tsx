'use client';

import { useEffect, useLayoutEffect } from 'react';
import { useAppStore } from '@/lib/store';

// 使用 useLayoutEffect 避免閃爍
const useIsomorphicLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useAppStore((state) => state.theme);

  useIsomorphicLayoutEffect(() => {
    // 強制在 html 元素上應用 dark class
    const root = document.documentElement;

    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
      root.style.colorScheme = 'dark';
    } else {
      root.classList.remove('dark');
      root.classList.add('light');
      root.style.colorScheme = 'light';
    }

    // 生產環境不輸出 console.log
  }, [theme]);

  return <>{children}</>;
}
