#!/bin/bash

# NIRAJ Development Servers Runner
# Starts all development services

set -e

echo "🚀 Starting NIRAJ Development Environment..."
echo "============================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to project root
cd "$(dirname "$0")/.."

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    log_info "Starting Redis server..."
    redis-server --daemonize yes || log_warning "Failed to start Redis"
else
    log_success "Redis already running"
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Starting Ollama server..."
    ollama serve &
    sleep 3
else
    log_success "Ollama already running"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    log_info "Shutting down development servers..."
    
    if [[ ! -z "$BACKEND_PID" ]]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [[ ! -z "$FRONTEND_PID" ]]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes
    pkill -f "uvicorn src.main:app" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    log_success "Development servers stopped"
    exit 0
}

# Setup cleanup on exit
trap cleanup INT TERM

# Start backend server
log_info "Starting backend server..."
cd backend
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend server
log_info "Starting frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Display status
echo ""
log_success "🎉 NIRAJ Development Environment Started!"
echo ""
echo "Services:"
echo "  📊 Backend API:    http://localhost:8000"
echo "  📚 API Docs:       http://localhost:8000/docs"
echo "  🖥️  Frontend:       http://localhost:5173"
echo "  🔴 Redis:          localhost:6379"
echo "  🤖 Ollama:         http://localhost:11434"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "Logs will appear below..."
echo ""

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID