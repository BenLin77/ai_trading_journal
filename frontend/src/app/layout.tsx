import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/QueryProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { AuthWrapper } from "@/components/layout/AuthWrapper";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Trading Journal",
  description: "Smart Trading Journal System - AI-Powered Trade Review & Performance Analysis",
  // 安全措施 #4: 禁止搜尋引擎索引（這是私人交易日誌系統）
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
    },
  },
  // 網站圖標
  icons: {
    icon: '/icon.svg',
    apple: '/icon.svg',
  },
  // 額外的安全設定
  other: {
    'X-Robots-Tag': 'noindex, nofollow, noarchive',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // 防止主題閃爍的 inline script
  const themeScript = `
    (function() {
      try {
        var stored = localStorage.getItem('trading-journal-storage');
        if (stored) {
          var parsed = JSON.parse(stored);
          var theme = parsed.state && parsed.state.theme;
          if (theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        } else {
          document.documentElement.classList.add('dark');
        }
      } catch (e) {
        document.documentElement.classList.add('dark');
      }
    })();
  `;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${inter.variable} font-sans antialiased bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100`} suppressHydrationWarning>
        <QueryProvider>
          <ThemeProvider>
            <AuthWrapper>
              {children}
            </AuthWrapper>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
