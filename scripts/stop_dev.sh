#!/bin/bash

# NIRAJ Development Servers Stopper
# Stops all development services

echo "🛑 Stopping NIRAJ Development Environment..."
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Stop backend servers
log_info "Stopping backend servers..."
pkill -f "uvicorn src.main:app" && log_success "Backend stopped" || log_info "No backend processes found"

# Stop frontend servers
log_info "Stopping frontend servers..."
pkill -f "npm run dev" && log_success "Frontend npm process stopped" || log_info "No frontend npm processes found"
pkill -f "vite" && log_success "Vite process stopped" || log_info "No Vite processes found"

# Stop Ollama (optional - user choice)
if [[ "$1" == "--all" ]]; then
    log_info "Stopping Ollama server..."
    pkill -f "ollama serve" && log_success "Ollama stopped" || log_info "No Ollama processes found"
    
    log_info "Stopping Redis server..."
    redis-cli shutdown && log_success "Redis stopped" || log_info "Redis stop command failed"
fi

log_success "🎉 NIRAJ Development servers stopped"

if [[ "$1" != "--all" ]]; then
    echo ""
    echo "Note: Redis and Ollama are still running"
    echo "Use './scripts/stop_dev.sh --all' to stop everything"
fi