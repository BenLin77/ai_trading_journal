#!/bin/bash
# ============================================================
# AI Trading Journal - 統一管理腳本
# ============================================================
# 用法: ./journal.sh [command]
#
# Commands:
#   start       啟動開發模式 (前後端 hot-reload)
#   start-prod  啟動生產模式
#   stop        停止所有服務
#   restart     重啟服務
#   status      查看服務狀態
#   build       構建前端生產版本
#   install     安裝依賴
#   logs        查看日誌
#   help        顯示幫助
# ============================================================

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 進入專案根目錄
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

# ============================================================
# 輔助函數
# ============================================================

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

show_help() {
    echo -e "${BLUE}AI Trading Journal - 管理腳本${NC}"
    echo ""
    echo "用法: ./journal.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       啟動開發模式 (hot-reload)"
    echo "  start-prod  啟動生產模式"
    echo "  stop        停止所有服務"
    echo "  restart     重啟服務"
    echo "  status      查看服務狀態"
    echo "  build       構建前端生產版本"
    echo "  install     安裝所有依賴"
    echo "  logs        查看 systemd 日誌"
    echo "  help        顯示此幫助"
    echo ""
}

# ============================================================
# stop - 停止服務
# ============================================================

cmd_stop() {
    log "Stopping AI Trading Journal..."
    
    local STOPPED=false
    
    # 使用 PID 文件停止
    for pidfile in .backend.pid .frontend.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID" 2>/dev/null || true
                sleep 1
                kill -9 "$PID" 2>/dev/null || true
                STOPPED=true
            fi
            rm -f "$pidfile"
        fi
    done
    
    # 按端口停止
    for port in 8000 3000; do
        if command -v lsof &>/dev/null && lsof -ti:$port &>/dev/null; then
            kill $(lsof -ti:$port) 2>/dev/null || true
            sleep 1
            kill -9 $(lsof -ti:$port) 2>/dev/null || true
            STOPPED=true
        fi
    done
    
    # 清理 Next.js lock
    rm -f frontend/.next/dev/lock 2>/dev/null || true
    
    if [ "$STOPPED" = true ]; then
        success "Services stopped"
    else
        echo "No running services found"
    fi
}

# ============================================================
# start - 開發模式
# ============================================================

cmd_start() {
    log "Starting AI Trading Journal (Development Mode)..."
    
    # 前置檢查
    check_prerequisites
    
    # 停止現有服務
    cmd_stop 2>/dev/null || true
    sleep 1
    
    # 啟動後端
    log "Starting backend (port 8000)..."
    cd backend
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    echo "$BACKEND_PID" > .backend.pid
    
    sleep 3
    
    # 啟動前端
    log "Starting frontend (port 3000)..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo "$FRONTEND_PID" > .frontend.pid
    
    sleep 2
    
    echo ""
    success "Development servers started!"
    echo ""
    echo "   🔧 Backend:  http://localhost:8000"
    echo "   📊 API Docs: http://localhost:8000/docs"
    echo "   🎨 Frontend: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop"
    
    trap "cmd_stop; exit 0" INT TERM
    wait
}

# ============================================================
# start-prod - 生產模式
# ============================================================

cmd_start_prod() {
    log "Starting AI Trading Journal (Production Mode)..."
    
    export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
    
    # 載入 .env
    [ -f ".env" ] && { set -a; source .env; set +a; }
    
    # 啟動後端
    log "Starting backend (port 8000)..."
    cd backend
    ${UV_PATH:-/root/.local/bin/uv} run uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 &
    BACKEND_PID=$!
    cd ..
    echo "$BACKEND_PID" > .backend.pid
    
    sleep 3
    
    # 啟動前端
    log "Starting frontend (port 3000)..."
    cd frontend
    if [ -d ".next" ] && [ -f ".next/BUILD_ID" ]; then
        /usr/bin/npm run start &
    else
        /usr/bin/npm run dev &
    fi
    FRONTEND_PID=$!
    cd ..
    echo "$FRONTEND_PID" > .frontend.pid
    
    success "Production servers started (Backend: $BACKEND_PID, Frontend: $FRONTEND_PID)"
    
    trap "cmd_stop; exit 0" INT TERM
    wait
}

# ============================================================
# restart - 重啟
# ============================================================

cmd_restart() {
    cmd_stop
    sleep 2
    if [ "${1:-}" = "--prod" ]; then
        cmd_start_prod
    else
        cmd_start
    fi
}

# ============================================================
# status - 狀態檢查
# ============================================================

cmd_status() {
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}          AI Trading Journal - Status              ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
    
    # 服務狀態
    echo -e "${CYAN}Services:${NC}"
    
    for port_name in "8000:Backend" "3000:Frontend"; do
        port=${port_name%%:*}
        name=${port_name##*:}
        if command -v lsof &>/dev/null && lsof -ti:$port &>/dev/null; then
            pid=$(lsof -ti:$port | head -1)
            echo -e "  $name (port $port): ${GREEN}● Running (PID: $pid)${NC}"
        else
            echo -e "  $name (port $port): ${RED}○ Stopped${NC}"
        fi
    done
    
    # systemd 狀態
    if systemctl is-active --quiet journal.service 2>/dev/null; then
        echo -e "  Systemd service:    ${GREEN}● Active${NC}"
    else
        echo -e "  Systemd service:    ${YELLOW}○ Inactive${NC}"
    fi
    
    echo ""
    
    # 健康檢查
    echo -e "${CYAN}Health:${NC}"
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null | grep -q "200"; then
        echo -e "  Backend API: ${GREEN}● Healthy${NC}"
    else
        echo -e "  Backend API: ${RED}○ Unreachable${NC}"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -qE "200|304"; then
        echo -e "  Frontend:    ${GREEN}● Healthy${NC}"
    else
        echo -e "  Frontend:    ${RED}○ Unreachable${NC}"
    fi
    
    echo ""
}

# ============================================================
# build - 構建前端
# ============================================================

cmd_build() {
    log "Building frontend..."
    
    cd frontend
    
    [ ! -d "node_modules" ] && npm install
    
    NODE_ENV=production npm run build
    
    cd ..
    
    success "Build completed!"
    [ -f "frontend/.next/BUILD_ID" ] && echo "Build ID: $(cat frontend/.next/BUILD_ID)"
}

# ============================================================
# install - 安裝依賴
# ============================================================

cmd_install() {
    log "Installing dependencies..."
    
    # 後端
    log "Installing backend dependencies..."
    cd backend && uv sync && cd ..
    success "Backend ready"
    
    # 前端
    log "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    success "Frontend ready"
    
    # 建立目錄
    mkdir -p data reports
    
    # 環境變數
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        warn "Created .env from .env.example - please edit it"
    fi
    
    success "Installation complete!"
}

# ============================================================
# logs - 查看日誌
# ============================================================

cmd_logs() {
    if systemctl is-active --quiet journal.service 2>/dev/null; then
        journalctl -u journal.service -f
    else
        warn "systemd service not running"
        echo "Use './journal.sh start' to run in foreground mode"
    fi
}

# ============================================================
# 前置檢查
# ============================================================

check_prerequisites() {
    # Node.js
    if ! command -v node &>/dev/null; then
        error "Node.js not found"
        exit 1
    fi
    
    local NODE_VER=$(node -v | sed 's/v//' | cut -d'.' -f1)
    if [ "$NODE_VER" -lt 20 ]; then
        error "Node.js 20+ required (current: v$NODE_VER)"
        exit 1
    fi
    
    # uv
    if ! command -v uv &>/dev/null; then
        error "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # 前端依賴
    if [ ! -d "frontend/node_modules" ]; then
        warn "Installing frontend dependencies..."
        cd frontend && npm install && cd ..
    fi
}

# ============================================================
# 主程式
# ============================================================

case "${1:-help}" in
    start)
        cmd_start
        ;;
    start-prod|prod)
        cmd_start_prod
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart "${2:-}"
        ;;
    status)
        cmd_status
        ;;
    build)
        cmd_build
        ;;
    install)
        cmd_install
        ;;
    logs)
        cmd_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
