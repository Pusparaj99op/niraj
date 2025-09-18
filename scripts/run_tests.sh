#!/bin/bash

# NIRAJ Test Runner
# Runs all test suites

set -e

echo "🧪 Running NIRAJ Test Suite..."
echo "==============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to project root
cd "$(dirname "$0")/.."

# Backend tests
run_backend_tests() {
    log_info "Running backend tests..."
    cd backend
    
    if [[ -d "tests" ]]; then
        # Run pytest with coverage
        poetry run pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
        
        if [[ $? -eq 0 ]]; then
            log_success "Backend tests passed"
        else
            log_error "Backend tests failed"
            return 1
        fi
    else
        log_warning "No backend tests found (tests directory doesn't exist)"
    fi
    
    cd ..
}

# Frontend tests  
run_frontend_tests() {
    log_info "Running frontend tests..."
    cd frontend
    
    # Check if test script exists
    if npm run --silent test --dry-run 2>/dev/null; then
        npm run test
        
        if [[ $? -eq 0 ]]; then
            log_success "Frontend tests passed"
        else
            log_error "Frontend tests failed"
            return 1
        fi
    else
        log_warning "No frontend tests configured"
    fi
    
    cd ..
}

# Linting and formatting checks
run_linting() {
    log_info "Running code quality checks..."
    
    # Backend linting
    cd backend
    log_info "Checking backend code quality..."
    
    # Flake8 linting
    if poetry run flake8 --version >/dev/null 2>&1; then
        poetry run flake8 src/ || log_warning "Linting issues found in backend"
    fi
    
    # Black formatting check
    if poetry run black --version >/dev/null 2>&1; then
        poetry run black --check src/ || log_warning "Formatting issues found in backend"
    fi
    
    # MyPy type checking
    if poetry run mypy --version >/dev/null 2>&1; then
        poetry run mypy src/ || log_warning "Type checking issues found"
    fi
    
    cd ..
    
    # Frontend linting (if configured)
    cd frontend
    log_info "Checking frontend code quality..."
    
    if npm run --silent lint --dry-run 2>/dev/null; then
        npm run lint || log_warning "Frontend linting issues found"
    else
        log_info "Frontend linting not configured"
    fi
    
    cd ..
}

# Integration tests (when available)
run_integration_tests() {
    log_info "Running integration tests..."
    cd backend
    
    if [[ -d "tests/integration" ]]; then
        poetry run pytest tests/integration/ -v --tb=short
        
        if [[ $? -eq 0 ]]; then
            log_success "Integration tests passed"
        else
            log_error "Integration tests failed"
            return 1
        fi
    else
        log_warning "No integration tests found"
    fi
    
    cd ..
}

# Main test function
main() {
    local test_type="$1"
    local exit_code=0
    
    case "$test_type" in
        "backend"|"be")
            run_backend_tests || exit_code=1
            ;;
        "frontend"|"fe")
            run_frontend_tests || exit_code=1
            ;;
        "lint"|"quality")
            run_linting || exit_code=1
            ;;
        "integration"|"int")
            run_integration_tests || exit_code=1
            ;;
        "all"|"")
            log_info "Running all tests..."
            
            run_linting || exit_code=1
            run_backend_tests || exit_code=1
            run_frontend_tests || exit_code=1
            run_integration_tests || exit_code=1
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [test_type]"
            echo ""
            echo "Test types:"
            echo "  all (default)  - Run all tests"
            echo "  backend, be    - Run backend tests only"
            echo "  frontend, fe   - Run frontend tests only"
            echo "  lint, quality  - Run code quality checks"
            echo "  integration    - Run integration tests"
            echo "  help           - Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown test type: $test_type"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    echo ""
    if [[ $exit_code -eq 0 ]]; then
        log_success "🎉 All tests completed successfully!"
    else
        log_error "❌ Some tests failed"
    fi
    
    exit $exit_code
}

# Run main function with arguments
main "$@"