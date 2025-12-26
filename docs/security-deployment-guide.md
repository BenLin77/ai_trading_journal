# AI Trading Journal - 安全部署指南

本文檔說明已實施的安全措施及部署步驟。

## 📋 安全措施清單

### ✅ 1. 環境變數完整設定
- **檔案**: `.env.example`, `.env`
- **說明**: 所有敏感資訊（API Keys、DB URL）都透過環境變數設定
- **動作**: 
  - 確保 `.env` 不在版本控制中（已在 `.gitignore`）
  - 在 Vercel/生產環境中設定所有必要的環境變數

### ✅ 2. 禁止公開後端 API
- **檔案**: `backend/main.py`, `journal.nginx.ssl.conf`
- **說明**: 
  - 生產環境禁用 Swagger UI (`/docs`) 和 OpenAPI (`/openapi.json`)
  - Nginx 層面限制 API 文檔只能內網訪問
  - CORS 設定限制只允許正式網域
- **動作**: 設定 `ENVIRONMENT=production` 環境變數

### ❌ 3. 加入機器人防護（用戶選擇跳過）
- 如需實施，可考慮：
  - Cloudflare Turnstile
  - Google reCAPTCHA
  - Upstash Rate Limit + Edge Middleware

### ✅ 4. robots.txt / noindex 控制
- **檔案**: 
  - `frontend/public/robots.txt`
  - `frontend/next.config.ts`
  - `frontend/src/app/layout.tsx`
- **說明**: 
  - `robots.txt` 禁止搜尋引擎抓取敏感頁面
  - Next.js 設定自動為敏感頁面加入 `X-Robots-Tag: noindex`
  - Layout metadata 設定 `robots.index: false`

### ✅ 5. 錯誤處理與回退頁
- **檔案**: 
  - `frontend/src/app/not-found.tsx` - 404 錯誤頁
  - `frontend/src/app/error.tsx` - 一般錯誤頁
  - `frontend/src/app/global-error.tsx` - 全域錯誤邊界
- **說明**: 
  - 自訂錯誤頁面，只顯示錯誤代碼（digest）
  - 不暴露堆疊追蹤或敏感錯誤訊息

### ✅ 6. 日誌與監控
- **檔案**: 
  - `frontend/src/app/error.tsx` - 預留 Sentry 整合接口
  - `.env.example` - 包含 `SENTRY_DSN` 設定
- **說明**: 已預留 Sentry 整合接口
- **動作**: 
  1. 到 [sentry.io](https://sentry.io) 建立專案
  2. 安裝 `@sentry/nextjs`: `npm install @sentry/nextjs`
  3. 執行設定: `npx @sentry/wizard@latest -i nextjs`
  4. 設定 `SENTRY_DSN` 環境變數

### ✅ 7. HTTPS 與網域設定完整
- **檔案**: 
  - `journal.nginx.ssl.conf` - 完整的 SSL Nginx 設定
  - `nginx-rate-limit.conf` - Rate Limiting 設定
  - `setup-ssl.sh` - SSL 自動設定腳本
  - `frontend/next.config.ts` - 安全 Headers
- **說明**: 
  - HTTP 自動重導向到 HTTPS
  - 現代 TLS 協議（TLSv1.2, TLSv1.3）
  - HSTS、X-Frame-Options 等安全 headers
  - Cookie 安全設定（HttpOnly, Secure, SameSite）

### ✅ 8. 付費成本上限控制
- **檔案**: 
  - `utils/rate_limiter.py` - API 速率限制模組
  - `.env.example` - 包含限額設定
- **說明**: 
  - `AI_DAILY_LIMIT=100` - 每日 AI 請求上限
  - `AI_HOURLY_LIMIT=20` - 每小時 AI 請求上限
  - `API_RATE_LIMIT=60` - 每分鐘 API 請求上限
- **動作**: 根據需求調整 `.env` 中的限額

### ✅ 9. 前端禁用開發用 console 資訊
- **檔案**: 
  - `frontend/next.config.ts` - compiler.removeConsole 設定
  - `frontend/src/providers/ThemeProvider.tsx` - 移除 console.log
- **說明**: 
  - 生產環境自動移除所有 `console.log`
  - 保留 `console.error` 和 `console.warn` 以便排錯

---

## 🚀 部署步驟

### 1. 設定 SSL（HTTPS）

```bash
# 執行 SSL 設定腳本
sudo ./setup-ssl.sh
```

腳本會自動：
- 安裝 Certbot
- 取得 Let's Encrypt SSL 憑證
- 設定 Nginx HTTPS
- 設定自動更新

### 2. 設定環境變數

```bash
# 複製 .env.example 並填入真實值
cp .env.example .env

# 必須設定的變數：
ENVIRONMENT=production        # 啟用所有生產環境安全措施
DEEPSEEK_API_KEY=sk-xxx      # 或 GEMINI_API_KEY
AI_DAILY_LIMIT=100           # 根據預算調整
```

### 3. 更新 Nginx 設定

```bash
# 確保 Rate Limiting 設定已加入
sudo grep -q "nginx-rate-limit.conf" /etc/nginx/nginx.conf || \
  sudo sed -i '/http {/a \    include /root/ai_trading_journal/nginx-rate-limit.conf;' /etc/nginx/nginx.conf

# 測試並重啟
sudo nginx -t && sudo systemctl reload nginx
```

### 4. 重建前端

```bash
cd frontend
npm run build
```

### 5. 重啟服務

```bash
sudo systemctl restart journal-ai
```

---

## 🔍 驗證清單

### 安全 Headers 驗證
```bash
curl -I https://journal.gamma-level.cc
```

應該看到：
- `Strict-Transport-Security: max-age=...`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`

### API 文檔保護驗證
```bash
# 應該返回 403 或 404
curl https://journal.gamma-level.cc/docs
curl https://journal.gamma-level.cc/openapi.json
```

### Rate Limiting 驗證
```bash
# 快速發送多個請求，應該收到 429 Too Many Requests
for i in {1..100}; do curl -o /dev/null -s -w "%{http_code}\n" https://journal.gamma-level.cc/api/health; done
```

### robots.txt 驗證
```bash
curl https://journal.gamma-level.cc/robots.txt
```

---

## 📊 監控設定（可選）

### Sentry 設定
```bash
cd frontend
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

### Vercel Analytics
如果部署到 Vercel：
```bash
npm install @vercel/analytics
```

然後在 `layout.tsx` 加入：
```tsx
import { Analytics } from '@vercel/analytics/react';
// ... 在 body 中加入 <Analytics />
```

---

## 📁 新增/修改的檔案清單

| 檔案 | 類型 | 用途 |
|------|------|------|
| `frontend/public/robots.txt` | 新增 | 搜尋引擎控制 |
| `frontend/src/app/not-found.tsx` | 新增 | 404 錯誤頁 |
| `frontend/src/app/error.tsx` | 新增 | 一般錯誤頁 |
| `frontend/src/app/global-error.tsx` | 新增 | 全域錯誤邊界 |
| `frontend/next.config.ts` | 修改 | 安全 headers、removeConsole |
| `frontend/src/app/layout.tsx` | 修改 | noindex metadata |
| `frontend/src/providers/ThemeProvider.tsx` | 修改 | 移除 console.log |
| `backend/main.py` | 修改 | 禁用 API 文檔、CORS 限制 |
| `utils/rate_limiter.py` | 新增 | API 限額控制 |
| `journal.nginx.ssl.conf` | 新增 | SSL Nginx 設定 |
| `nginx-rate-limit.conf` | 新增 | Rate Limiting 設定 |
| `setup-ssl.sh` | 新增 | SSL 自動設定腳本 |
| `.env.example` | 修改 | 新增安全相關變數 |
