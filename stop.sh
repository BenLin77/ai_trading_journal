#!/bin/bash
# 停止 AI Trading Journal 服務
# 用法: ./stop.sh

set -euo pipefail

echo "🛑 正在停止 AI Trading Journal 服務..."

# 停止後端 (FastAPI/Uvicorn on port 8000)
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "  → 停止後端 (port 8000)..."
    kill $(lsof -ti:8000) 2>/dev/null || true
    echo "  ✅ 後端已停止"
else
    echo "  ⚪ 後端未運行"
fi

# 停止前端 (Next.js on port 3000)
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "  → 停止前端 (port 3000)..."
    kill $(lsof -ti:3000) 2>/dev/null || true
    echo "  ✅ 前端已停止"
else
    echo "  ⚪ 前端未運行"
fi

# 清除 Next.js lock 文件（避免下次啟動問題）
if [ -f "frontend/.next/dev/lock" ]; then
    rm -f frontend/.next/dev/lock
    echo "  🧹 已清除 Next.js lock 文件"
fi

echo ""
echo "✅ 所有服務已停止"
