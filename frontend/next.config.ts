import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 生產環境移除 console.log（安全措施 #9）
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],  // 保留 error 和 warn 以便排錯
    } : false,
  },

  // 安全 Headers（安全措施 #5, #7）
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          // 防止 Clickjacking
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          // 防止 MIME 類型嗅探
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          // XSS 防護
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          // 強制 HTTPS
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
          // Referrer 政策
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          // 權限政策
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
      // 敏感頁面禁止搜尋引擎索引（安全措施 #4）
      {
        source: '/settings/:path*',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
      {
        source: '/journal/:path*',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
      {
        source: '/report/:path*',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
      {
        source: '/ai/:path*',
        headers: [
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow',
          },
        ],
      },
    ];
  },

  // 環境變數前綴（只有 NEXT_PUBLIC_ 開頭的才會暴露給前端）
  env: {
    // 不要在這裡放敏感資訊！
  },

  // 圖片優化設定（使用 remotePatterns 替代已棄用的 domains）
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'journal.gamma-level.cc',
        pathname: '/**',
      },
    ],
  },

  // API 代理（開發和生產環境都使用）
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
