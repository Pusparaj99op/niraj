# NIRAJ Development Scripts

This directory contains automation scripts for the NIRAJ trading system development and deployment.

## Scripts Overview

### 🚀 `setup_dev.sh` - Development Environment Setup
Complete setup script for development environment.

**Usage:**
```bash
./scripts/setup_dev.sh
```

**What it does:**
- Checks prerequisites (Python 3.11+, Poetry, Node.js, etc.)
- Sets up backend with Poetry dependencies
- Initializes frontend with npm dependencies
- Configures Ollama AI model
- Sets up Redis server
- Initializes database
- Creates development configuration files
- Runs health checks

### 🏃‍♂️ `run_dev.sh` - Start Development Servers
Starts all development services in one command.

**Usage:**
```bash
./scripts/run_dev.sh
```

**Services started:**
- Backend API server (http://localhost:8000)
- Frontend dev server (http://localhost:5173) 
- Redis server
- Ollama AI server

**Features:**
- Automatic cleanup on Ctrl+C
- Color-coded logging
- Service status monitoring

### 🛑 `stop_dev.sh` - Stop Development Servers
Stops all development services.

**Usage:**
```bash
./scripts/stop_dev.sh        # Stop dev servers only
./scripts/stop_dev.sh --all  # Stop everything including Redis and Ollama
```

### 🧪 `run_tests.sh` - Test Runner
Comprehensive test runner for all test types.

**Usage:**
```bash
./scripts/run_tests.sh [test_type]
```

**Test types:**
- `all` (default) - Run all tests
- `backend` or `be` - Backend tests only
- `frontend` or `fe` - Frontend tests only  
- `lint` or `quality` - Code quality checks
- `integration` or `int` - Integration tests

**Features:**
- pytest with coverage for backend
- ESLint/Prettier for frontend
- Black/Flake8/MyPy for Python code quality
- Detailed reporting

### 💾 `db_manager.sh` - Database Management
Database operations and management.

**Usage:**
```bash
./scripts/db_manager.sh [operation]
```

**Operations:**
- `init` - Initialize database with tables
- `reset` - Reset database (⚠️ deletes all data)
- `backup` - Create database backup
- `check` - Health check and statistics
- `migrate` - Run database migrations
- `seed` - Seed with sample data

**Features:**
- Automatic backups before destructive operations
- Health monitoring
- Safe reset with confirmation

### 🚢 `deploy.sh` - Production Deployment
Production deployment automation.

**Usage:**
```bash
./scripts/deploy.sh [operation]
```

**Operations:**
- `deploy` - Full deployment process
- `rollback` - Rollback to previous version
- `health` - Run health checks
- `nginx` - Setup Nginx configuration
- `service` - Setup systemd service

**Requirements:**
- Root/sudo access
- Environment variables set
- Production server setup

## Development Workflow

### Initial Setup
```bash
# Clone repository
git clone <repository-url>
cd niraj

# Run complete setup
./scripts/setup_dev.sh

# Start development servers
./scripts/run_dev.sh
```

### Daily Development
```bash
# Start servers
./scripts/run_dev.sh

# Run tests (in another terminal)
./scripts/run_tests.sh

# Stop servers when done
./scripts/stop_dev.sh
```

### Database Operations
```bash
# Check database status
./scripts/db_manager.sh check

# Reset database for testing
./scripts/db_manager.sh reset

# Create backup
./scripts/db_manager.sh backup
```

### Code Quality
```bash
# Run all tests and linting
./scripts/run_tests.sh

# Run only code quality checks
./scripts/run_tests.sh lint
```

## Environment Setup

### Prerequisites
- **Python 3.11+** - Core backend language
- **Poetry** - Python dependency management
- **Node.js 18+** - Frontend development
- **Redis** - Caching and real-time data
- **Ollama** - AI model serving

### Installation Commands

**Ubuntu/Debian:**
```bash
# Python 3.11
sudo apt update && sudo apt install python3.11 python3.11-pip

# Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs

# Redis
sudo apt install redis-server

# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11 poetry node redis

# Ollama
brew install ollama
```

## Configuration Files

### Backend Configuration
- `backend/.env` - Environment variables
- `backend/config/development.yaml` - Development settings
- `backend/config/production.yaml` - Production settings
- `backend/config/testing.yaml` - Test settings

### Frontend Configuration  
- `frontend/.env.local` - Frontend environment variables
- `frontend/vite.config.ts` - Vite configuration
- `frontend/tailwind.config.js` - Tailwind CSS settings

## Logging

All scripts provide colored, structured logging:

- 🔵 **INFO** - General information
- 🟢 **SUCCESS** - Successful operations
- 🟡 **WARNING** - Warnings and non-critical issues
- 🔴 **ERROR** - Errors and failures

Logs are saved to:
- `backend/logs/niraj.log` - Application logs
- `backend/logs/trading.log` - Trading activity logs
- `backend/logs/ai.log` - AI operation logs

## Troubleshooting

### Common Issues

**Script Permission Denied:**
```bash
chmod +x scripts/*.sh
```

**Poetry Not Found:**
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

**Redis Connection Failed:**
```bash
sudo systemctl start redis-server
# or
redis-server --daemonize yes
```

**Ollama Model Not Found:**
```bash
ollama pull gemma3:4b-it-q4_K_M
```

**Port Already in Use:**
```bash
# Kill processes on ports 8000/5173
lsof -ti:8000 | xargs kill
lsof -ti:5173 | xargs kill
```

### Getting Help

Each script has built-in help:
```bash
./scripts/[script_name].sh help
```

## Production Deployment

### Server Requirements
- Ubuntu 20.04+ or similar
- 4GB+ RAM
- 20GB+ storage
- Docker (optional)
- Nginx (reverse proxy)
- Systemd (service management)

### Deployment Process
1. Set environment variables
2. Run deployment script
3. Configure domain/SSL
4. Monitor logs and health

```bash
# Set environment variables
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."
export JWT_SECRET_KEY="..."

# Deploy
./scripts/deploy.sh deploy

# Check health
./scripts/deploy.sh health
```

## Security Notes

- 🔐 Never commit `.env` files
- 🔑 Use strong JWT secrets in production
- 🛡️ Configure firewall rules
- 📝 Regular security updates
- 🔍 Monitor logs for suspicious activity

## Contributing

When adding new scripts:
1. Follow the existing structure and style
2. Add comprehensive help text
3. Include error handling
4. Use color-coded logging
5. Update this README

---

**NIRAJ Development Team**  
Advanced Self-Learning Algorithmic AI Personal Trading System