import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/QueryProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { AIChat } from "@/components/chat/AIChat";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Trading Journal",
  description: "Smart Trading Journal System - AI-Powered Trade Review & Performance Analysis",
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
            <Header />
            <div className="flex">
              <Sidebar />
              <main className="flex-1 ml-64 min-h-[calc(100vh-4rem)] p-6">
                {children}
              </main>
            </div>
            <AIChat />
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
