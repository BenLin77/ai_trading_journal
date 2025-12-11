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

# 啟動 FastAPI 後端
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
