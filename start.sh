#!/bin/bash
# Start Claude History Viewer
# Backend: http://localhost:8787
# Frontend (dev): http://localhost:5173

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Claude History Viewer..."
echo ""

# Start backend in background
echo "Starting backend on http://localhost:8787"
python server.py --no-open &
BACKEND_PID=$!

# Start frontend dev server
echo "Starting frontend on http://localhost:5173"
cd web
npx vite --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "✓ Claude History Viewer is running!"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8787"
echo ""
echo "Press Ctrl+C to stop both servers."

# Handle cleanup
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

wait
