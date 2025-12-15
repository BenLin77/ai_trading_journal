#!/bin/bash
set -euo pipefail

# AI Trading Journal - Development Server Startup Script
# 啟動 FastAPI 後端和 Next.js 前端

echo "🚀 Starting AI Trading Journal..."
echo ""

# 確保在專案根目錄
cd "$(dirname "$0")"

# 檢查 .env 檔案
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Copy .env.example to .env and configure it."
fi

# 檢查 Node.js 版本 (Next.js 16 需要 Node.js 20+)
NODE_VERSION=$(node -v 2>/dev/null | sed 's/v//' | cut -d'.' -f1)
if [ -z "$NODE_VERSION" ]; then
    echo "❌ Node.js not found. Please install Node.js 20+"
    exit 1
fi

if [ "$NODE_VERSION" -lt 20 ]; then
    echo "⚠️  Node.js version too low (current: v$NODE_VERSION)"
    echo "   Next.js 16 requires Node.js 20+. Please run:"
    echo "   nvm install 20 && nvm use 20"
    exit 1
fi
echo "✅ Node.js version: v$NODE_VERSION"

# 啟動 FastAPI 後端
echo ""
echo "📦 Starting FastAPI backend on port 8000..."
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 等待後端啟動
sleep 3

# 啟動 Next.js 前端
echo "🎨 Starting Next.js frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Development servers started!"
echo ""
echo "   🔧 Backend API:  http://localhost:8000"
echo "   📊 API Docs:     http://localhost:8000/docs"
echo "   🎨 Frontend:     http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
