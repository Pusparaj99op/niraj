#!/bin/bash

# NIRAJ Development Setup Script
# Automates the complete setup process for NIRAJ development environment

set -e  # Exit on error

echo "🚀 NIRAJ Development Setup Starting..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python 3.11+
    if ! command -v python3.11 &> /dev/null; then
        log_warning "Python 3.11 not found, checking python3..."
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3 is required but not installed"
            exit 1
        fi
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        if [[ $(echo "$PYTHON_VERSION 3.11" | tr ' ' '\n' | sort -V | tail -n1) != "3.11" ]]; then
            log_error "Python 3.11+ is required. Found: $PYTHON_VERSION"
            exit 1
        fi
    fi
    
    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry is required but not installed"
        log_info "Install with: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required but not installed"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is required but not installed"
        exit 1
    fi
    
    # Check Redis
    if ! command -v redis-server &> /dev/null; then
        log_warning "Redis server not found - install with: sudo apt install redis-server"
    fi
    
    # Check Ollama
    if ! command -v ollama &> /dev/null; then
        log_warning "Ollama not found - install from https://ollama.ai"
    fi
    
    log_success "Prerequisites check completed"
}

# Setup backend
setup_backend() {
    log_info "Setting up backend..."
    
    cd backend
    
    # Install dependencies
    log_info "Installing Python dependencies..."
    poetry install
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        log_info "Creating .env file from template..."
        cp .env.template .env
        log_warning "Please update .env file with your API keys and settings"
    fi
    
    # Create directories
    log_info "Creating necessary directories..."
    mkdir -p data logs
    
    # Create __init__.py files
    find src -type d -exec touch {}/__init__.py \;
    
    cd ..
    log_success "Backend setup completed"
}

# Setup frontend
setup_frontend() {
    log_info "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies (already done during project init)
    log_info "Installing Node.js dependencies..."
    npm install
    
    # Create .env.local file if it doesn't exist
    if [ ! -f .env.local ]; then
        log_info "Creating .env.local file from template..."
        cp .env.template .env.local
    fi
    
    cd ..
    log_success "Frontend setup completed"
}

# Setup Ollama model
setup_ollama() {
    log_info "Setting up Ollama AI model..."
    
    if command -v ollama &> /dev/null; then
        # Start Ollama in background if not running
        if ! pgrep -x "ollama" > /dev/null; then
            log_info "Starting Ollama server..."
            ollama serve &
            sleep 3
        fi
        
        # Pull the model if not already available
        if ! ollama list | grep -q "gemma3:4b-it-q4_K_M"; then
            log_info "Downloading Gemma3 model (this may take a while)..."
            ollama pull gemma3:4b-it-q4_K_M
        else
            log_success "Gemma3 model already available"
        fi
        
        log_success "Ollama setup completed"
    else
        log_warning "Ollama not installed - skipping model setup"
    fi
}

# Setup Redis
setup_redis() {
    log_info "Setting up Redis..."
    
    if command -v redis-server &> /dev/null; then
        # Start Redis if not running
        if ! pgrep -x "redis-server" > /dev/null; then
            log_info "Starting Redis server..."
            redis-server --daemonize yes
        else
            log_success "Redis already running"
        fi
        
        # Test Redis connection
        if redis-cli ping | grep -q "PONG"; then
            log_success "Redis setup completed"
        else
            log_error "Redis connection test failed"
        fi
    else
        log_warning "Redis not installed - skipping Redis setup"
    fi
}

# Create development database
setup_database() {
    log_info "Setting up database..."
    
    cd backend
    
    # Create database using Python script
    poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import init_database
    asyncio.run(init_database())
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization failed: {e}')
    sys.exit(1)
"
    
    cd ..
    log_success "Database setup completed"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    # Check backend can start
    log_info "Testing backend startup..."
    cd backend
    timeout 10s poetry run python -c "
import sys
sys.path.insert(0, 'src')

try:
    from core.config import load_config, validate_config
    load_config()
    if validate_config():
        print('Backend configuration valid')
    else:
        print('Backend configuration invalid')
        sys.exit(1)
except Exception as e:
    print(f'Backend startup test failed: {e}')
    sys.exit(1)
" || log_warning "Backend startup test failed or timed out"
    
    cd ..
    
    # Check frontend can build
    log_info "Testing frontend build..."
    cd frontend
    timeout 30s npm run build > /dev/null 2>&1 && log_success "Frontend build test passed" || log_warning "Frontend build test failed"
    
    cd ..
    log_success "Health checks completed"
}

# Create development scripts
create_scripts() {
    log_info "Creating development scripts..."
    
    # Create run script
    cat > scripts/run_dev.sh << 'EOF'
#!/bin/bash
# Start NIRAJ development servers

echo "Starting NIRAJ development environment..."

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
fi

# Start Ollama if not running  
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Start backend in background
echo "Starting backend..."
cd backend && poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend in background
echo "Starting frontend..."
cd ../frontend && npm run dev &
FRONTEND_PID=$!

echo "NIRAJ development servers started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop all servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
EOF
    
    chmod +x scripts/run_dev.sh
    
    # Create stop script
    cat > scripts/stop_dev.sh << 'EOF'
#!/bin/bash
# Stop NIRAJ development servers

echo "Stopping NIRAJ development servers..."

# Kill backend
pkill -f "uvicorn src.main:app"

# Kill frontend
pkill -f "npm run dev"
pkill -f "vite"

echo "Development servers stopped"
EOF
    
    chmod +x scripts/stop_dev.sh
    
    # Create test script
    cat > scripts/run_tests.sh << 'EOF'
#!/bin/bash
# Run NIRAJ tests

echo "Running NIRAJ tests..."

# Backend tests
echo "Running backend tests..."
cd backend && poetry run pytest tests/ -v

# Frontend tests (when implemented)
# cd ../frontend && npm test

echo "Tests completed"
EOF
    
    chmod +x scripts/run_tests.sh
    
    log_success "Development scripts created"
}

# Main setup function
main() {
    echo "NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System"
    echo "Development Environment Setup"
    echo ""
    
    check_prerequisites
    setup_backend
    setup_frontend
    setup_ollama
    setup_redis
    setup_database
    create_scripts
    run_health_checks
    
    echo ""
    echo "🎉 NIRAJ Development Setup Complete!"
    echo "====================================="
    echo ""
    echo "Next steps:"
    echo "1. Update backend/.env with your API keys"
    echo "2. Update frontend/.env.local if needed"
    echo "3. Start development servers: ./scripts/run_dev.sh"
    echo ""
    echo "Available scripts:"
    echo "  ./scripts/run_dev.sh    - Start development servers"
    echo "  ./scripts/stop_dev.sh   - Stop development servers"
    echo "  ./scripts/run_tests.sh  - Run tests"
    echo ""
    echo "Documentation:"
    echo "  Backend:  http://localhost:8000/docs"
    echo "  Frontend: http://localhost:5173"
    echo ""
    log_success "Setup completed successfully! 🚀"
}

# Run main function
main "$@"