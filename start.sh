#!/bin/bash
# AI Data Studio — 一鍵啟動腳本

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 啟動 AI Data Studio..."
echo ""

# 關閉舊的伺服器（若有）
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "http.server 8080" 2>/dev/null
sleep 1

# 啟動後端 FastAPI (port 8000)
echo "⚡ 啟動後端伺服器 (port 8000)..."
cd "$PROJECT_DIR/backend"
.venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 啟動前端靜態伺服器 (port 8080)
echo "🌐 啟動前端伺服器 (port 8080)..."
cd "$PROJECT_DIR"
python3 -m http.server 8080 --directory "$PROJECT_DIR" &
FRONTEND_PID=$!

echo ""
echo "✅ 啟動完成！"
echo ""
echo "   Dashboard: http://localhost:8080/frontend/index.html"
echo "   設定頁面:  http://localhost:8080/frontend/settings.html"
echo "   API 文件:  http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 關閉所有伺服器"

# 等待任一子程序結束
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已關閉所有伺服器'; exit" INT TERM
wait
