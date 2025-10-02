# Type Checking Error Resolution - Quick Start Guide

**Date**: 17 September 2025
**Version**: 1.0.0
**Target Audience**: Developers working on NIRAJ codebase

## Overview

This guide provides quick validation procedures for the type checking error resolution implementation. Use this to verify that type checking fixes are working correctly and that the codebase passes all type checks.

## Prerequisites

### System Requirements
- **Python**: 3.11+ installed
- **Poetry**: For dependency management
- **Mypy**: Type checker (installed via Poetry)
- **Flake8**: Linter (installed via Poetry)

### Environment Setup
```bash
# Ensure you're in the project root
cd /home/pranay/Music/niraj

# Activate Poetry environment
cd backend
poetry shell
```

## Quick Validation (5 Minutes)

### 1. Run Type Checking
```bash
# From backend directory with Poetry shell active
cd backend

# Run mypy type checking
mypy --config-file ../pyproject.toml src/

# Expected: No errors (0 errors found)
```

### 2. Run Linting
```bash
# Run flake8 linting
flake8 --config ../setup.cfg src/

# Expected: No F401 errors or other critical issues
```

### 3. Run Tests with Type Coverage
```bash
# Run pytest with type checking
pytest --mypy --strict-markers tests/

# Expected: All tests pass with type coverage
```

## Validation Procedures

### Success Criteria

#### ✅ Type Check Success
- **Mypy**: 0 errors across all 111 Python files
- **Error Categories**: All resolved (missing annotations, incompatible types, missing stubs, etc.)
- **Type Coverage**: 100% for critical modules

#### ✅ Code Quality Success
- **Flake8**: No F401 unused import errors
- **Import Organization**: All imports properly used or removed
- **Code Style**: Consistent with project standards

#### ✅ Test Success
- **Unit Tests**: All pass with type checking enabled
- **Integration Tests**: Type-safe API interactions
- **Coverage**: >90% type-annotated code

### Validation Commands

#### Full Type Check Suite
```bash
#!/bin/bash
# Run from backend directory

echo "=== Running Full Type Check Suite ==="

# 1. Mypy strict checking
echo "1. Running mypy..."
mypy --config-file ../pyproject.toml src/
MYPY_EXIT=$?

# 2. Flake8 import checking
echo "2. Running flake8..."
flake8 --config ../setup.cfg --select=F401 src/
FLAKE8_EXIT=$?

# 3. Test with type checking
echo "3. Running tests with mypy..."
pytest --mypy --tb=short tests/
TEST_EXIT=$?

# Summary
echo "=== Validation Results ==="
echo "Mypy: $([ $MYPY_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")"
echo "Flake8: $([ $FLAKE8_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")"
echo "Tests: $([ $TEST_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")"

# Exit with failure if any check failed
[ $MYPY_EXIT -eq 0 ] && [ $FLAKE8_EXIT -eq 0 ] && [ $TEST_EXIT -eq 0 ]
```

#### Quick Health Check
```bash
# Quick validation (run frequently during development)
cd backend
poetry run mypy --config-file ../pyproject.toml src/ | head -20
poetry run flake8 --config ../setup.cfg --select=F401 src/ | wc -l
```

## Error Resolution Verification

### Common Error Patterns

#### 1. Missing Type Annotations
**Before Fix:**
```python
def process_data(data):  # Error: missing parameter type
    return data * 2     # Error: missing return type
```

**After Fix:**
```python
def process_data(data: dict) -> dict:  # ✅ Fixed
    return data
```

**Validation:**
```bash
# Check specific function
mypy --config-file ../pyproject.toml src/path/to/file.py | grep "process_data"
# Expected: No errors
```

#### 2. Incompatible Types
**Before Fix:**
```python
def calculate_total(items: list) -> int:
    return sum(items)  # Error: list may contain non-numeric types
```

**After Fix:**
```python
def calculate_total(items: list[float]) -> float:
    return sum(items)  # ✅ Fixed with proper generics
```

**Validation:**
```bash
mypy --config-file ../pyproject.toml src/path/to/file.py
```

#### 3. Missing Type Stubs
**Before Fix:**
```python
import structlog  # Error: no type stubs available

logger = structlog.get_logger()
logger.info("message")  # Error: unknown method signatures
```

**After Fix:**
```python
# Install type stubs
poetry add --group dev types-structlog

# Or add type: ignore comments for external libs without stubs
import structlog  # type: ignore[import]
```

**Validation:**
```bash
poetry install
mypy --config-file ../pyproject.toml src/path/to/file.py
```

#### 4. Unused Imports (F401)
**Before Fix:**
```python
import os  # F401: unused import
import json
from typing import Dict

def process_data(data: Dict) -> str:
    return json.dumps(data)  # os not used
```

**After Fix:**
```python
import json
from typing import Dict

def process_data(data: Dict) -> str:
    return json.dumps(data)  # ✅ Removed unused import
```

**Validation:**
```bash
flake8 --config ../setup.cfg --select=F401 src/path/to/file.py
# Expected: No output
```

## Troubleshooting

### Common Issues

#### 1. Mypy Still Shows Errors
```bash
# Check mypy configuration
cat ../pyproject.toml | grep -A 10 "\[tool.mypy\]"

# Run mypy with verbose output
mypy --config-file ../pyproject.toml -v src/path/to/file.py

# Check if type stubs are installed
poetry show | grep types-
```

#### 2. Flake8 F401 Errors Persist
```bash
# Check flake8 configuration
cat ../setup.cfg | grep -A 5 "\[flake8\]"

# Run flake8 on specific file
flake8 --config ../setup.cfg --select=F401 src/path/to/file.py

# Check if imports are actually used
grep -n "unused_import" src/path/to/file.py
```

#### 3. Test Failures with Type Checking
```bash
# Run tests with detailed output
pytest --mypy -v tests/path/to/test_file.py

# Check test configuration
cat ../pyproject.toml | grep -A 5 "\[tool.pytest\]"
```

### Debug Commands

#### Find Remaining Errors
```bash
# Count mypy errors by file
cd backend
mypy --config-file ../pyproject.toml src/ 2>&1 | grep "error:" | cut -d: -f1 | sort | uniq -c | sort -nr

# Count F401 errors by file
flake8 --config ../setup.cfg --select=F401 src/ 2>&1 | cut -d: -f1 | sort | uniq -c | sort -nr
```

#### Check Type Coverage
```bash
# Install mypy coverage tool
poetry add --group dev mypy-coverage

# Generate coverage report
mypy-coverage src/ --config-file ../pyproject.toml

# Check specific module coverage
mypy-coverage src/core/ --config-file ../pyproject.toml
```

## Success Metrics

### Quantitative Metrics
- **Mypy Errors**: 0 (down from 3034)
- **F401 Errors**: 0 (down from 100+)
- **Type Coverage**: >95%
- **Test Pass Rate**: 100% with type checking

### Qualitative Metrics
- **Code Readability**: Improved with explicit types
- **IDE Support**: Better autocomplete and error detection
- **Maintainability**: Easier refactoring with type safety
- **Bug Prevention**: Fewer runtime type-related errors

## Next Steps

### After Validation Success
1. **Enable Strict Mode**: Update mypy config for even stricter checking
2. **Add Pre-commit Hooks**: Automate type checking in CI/CD
3. **Documentation**: Update API docs with type information
4. **Team Training**: Educate team on type-driven development

### Continuous Improvement
1. **Regular Audits**: Weekly type coverage checks
2. **New Code Standards**: Require types for all new code
3. **Stub Development**: Create stubs for internal libraries
4. **Performance Monitoring**: Track type check execution time

## Resources

### Configuration Files
- `../pyproject.toml` - Mypy and Poetry configuration
- `../setup.cfg` - Flake8 configuration
- `../requirements.txt` - Additional dependencies

### Documentation
- `research.md` - Detailed error analysis and solutions
- `data-model.md` - Type checking data structures
- `contracts/type-check-api.md` - API validation contracts

### Tools
- **Mypy Docs**: https://mypy.readthedocs.io/
- **Flake8 Docs**: https://flake8.pycqa.org/
- **Typing Module**: https://docs.python.org/3/library/typing.html

---

**✅ Validation Complete**: When all commands return success (0 errors), the type checking error resolution is complete and the codebase is type-safe.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 22.04 LTS (or similar Linux distribution)
- **Hardware**: Minimum 8GB RAM, 4 CPU cores, 50GB storage
- **Python**: 3.11+ installed
- **Node.js**: 18+ installed for frontend
- **Git**: For version control

### Development Environment
- **IDE**: VS Code recommended
- **GPU**: NVIDIA GPU with CUDA support (optional, for AI acceleration)
- **Internet**: Stable connection for API access
- **Browser**: Chrome/Firefox for frontend testing

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/Pusparaj99op/NIRAJ.git
cd NIRAJ
```

### 2. Backend Setup

#### Install Poetry (Python package manager)
```bash
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
```

#### Install Python Dependencies
```bash
cd backend
poetry install
poetry shell  # Activate virtual environment
```

#### Install Ollama (AI Model)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Gemma3 model
ollama pull gemma2:2b
ollama serve  # Start Ollama service (keep running)
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. Database Setup
```bash
cd ../backend
# Create database tables
python -m src.core.database_setup

# Load initial data (Bank Nifty constituents)
python -m src.utils.data_loader --setup-securities
```

### 5. Configuration

#### Create Configuration Files
```bash
# Copy example configurations
cp config/trading_config.example.yml config/trading_config.yml
cp config/api_config.example.yml config/api_config.yml
cp config/ai_config.example.yml config/ai_config.yml
```

#### Update API Configuration
Edit `config/api_config.yml`:
```yaml
angel_one:
  api_key: "your_angel_one_api_key"
  api_secret: "your_angel_one_secret"
  client_id: "your_client_id"

dhan:
  api_key: "your_dhan_api_key"  # Optional
  client_id: "your_dhan_client_id"

news_api:
  api_key: "your_news_api_key"

weather_api:
  api_key: "your_weather_api_key"
```

## Quick Start (5 Minutes)

### 1. Start Backend Services
```bash
cd backend
poetry shell

# Terminal 1: Start main application
python src/main.py

# Terminal 2: Start data manager (in background)
python -m src.core.data_manager &

# Terminal 3: Start information processor
python -m src.core.information_processor &
```

### 2. Start Frontend
```bash
cd frontend
npm run dev  # Starts on http://localhost:3005
```

### 3. Access the System
1. Open browser: `http://localhost:3005`
2. Default login: `username: admin, password: password`
3. System starts in **Paper Trading Mode** (safe)

### 4. Verify Setup
Check the dashboard for:
- ✅ API connections status
- ✅ AI model loaded (Gemma3)
- ✅ Market data streaming
- ✅ Virtual portfolio: ₹1,00,000

## First Trading Test (Paper Mode)

### 1. Enable a Strategy
1. Go to **Strategies** page
2. Enable "Predator Strategy" (lowest risk)
3. Set confidence threshold: `0.8` (conservative)
4. Click **Activate Strategy**

### 2. Monitor AI Analysis
1. Watch **AI Monitor** tab
2. Observe real-time market analysis
3. Check confidence scores and reasoning

### 3. View Generated Signals
1. Go to **Signals** page
2. Watch for strategy signals (BUY/SELL recommendations)
3. Note AI confidence levels and reasoning

### 4. Check Paper Trades
1. Go to **Trades** page
2. Monitor executed paper trades
3. View P&L calculations (virtual money)

## Switch to Live Trading (Advanced)

⚠️ **WARNING**: Only switch to live trading after thorough testing

### 1. Enable Live Mode
1. Click **Trading Mode** toggle
2. Enter PIN: `1937`
3. Confirm live trading activation

### 2. Set Capital Limits
1. Go to **Risk Management**
2. Set maximum daily loss: `₹5,000` (recommended)
3. Set position size limit: `10%` of capital
4. Enable circuit breakers

### 3. Start with Conservative Strategies
1. Begin with low-risk strategies only
2. Use smaller position sizes initially
3. Monitor performance closely
4. Gradually increase exposure

## API Testing

### 1. Test REST API
```bash
# Get system status
curl -X GET "http://localhost:8000/api/v1/system/status"

# Login and get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# Use token for authenticated requests
curl -X GET "http://localhost:8000/api/v1/strategies" \
  -H "Authorization: Bearer <your_token>"
```

### 2. Test WebSocket Connection
```bash
# Install wscat if not available
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost:8000/ws"

# Send authentication
> {"type":"auth","token":"<your_jwt_token>"}

# Subscribe to market data
> {"type":"subscribe","data":{"streams":[{"stream_type":"market_data","symbols":["BANKNIFTY"]}]}}
```

## Troubleshooting

### Common Issues

#### 1. Ollama Not Starting
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama service
sudo systemctl restart ollama

# Check Ollama models
ollama list
```

#### 2. API Connection Failures
```bash
# Check network connectivity
ping apiconnect.angelbroking.com

# Verify API credentials in logs
tail -f data/logs/api_client.log

# Test API endpoints manually
python -c "from src.api.angel_one_client import AngelOneClient; client = AngelOneClient(); print(client.test_connection())"
```

#### 3. Database Issues
```bash
# Reset database (CAUTION: loses data)
rm data/niraj.db
python -m src.core.database_setup

# Check database integrity
python -c "from src.core.database import DatabaseManager; db = DatabaseManager(); print(db.health_check())"
```

#### 4. Frontend Not Loading
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

#### 5. Port Conflicts
```bash
# Check if ports are in use
netstat -tlnp | grep :8000
netstat -tlnp | grep :3005

# Kill processes using ports
sudo lsof -ti:8000 | xargs kill
sudo lsof -ti:3005 | xargs kill
```

### Log Files
Check these files for debugging:
- `data/logs/main.log` - Main application logs
- `data/logs/trading.log` - Trading-specific logs
- `data/logs/api_client.log` - API communication logs
- `data/logs/ai_model.log` - AI model logs
- `data/logs/error.log` - Error logs

### Getting Help
1. Check logs first: `tail -f data/logs/main.log`
2. Verify configuration files
3. Test individual components
4. Check API connectivity
5. Review system status dashboard

## Security Checklist

### Before Live Trading
- [ ] API credentials secured and encrypted
- [ ] PIN protection enabled (1937)
- [ ] Risk limits properly configured
- [ ] Backup and recovery tested
- [ ] All strategies thoroughly backtested
- [ ] Circuit breakers enabled
- [ ] Audit logging activated
- [ ] System monitoring configured

### Regular Maintenance
- [ ] Daily log review
- [ ] Weekly system health check
- [ ] Monthly performance analysis
- [ ] Quarterly security audit
- [ ] Regular data backups
- [ ] API key rotation (quarterly)
- [ ] Strategy performance review

## Performance Optimization

### System Tuning
```bash
# Increase file descriptor limits
ulimit -n 65536

# Optimize Python garbage collection
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=1

# Use faster JSON library
pip install orjson ujson
```

### Database Optimization
```bash
# Regular database maintenance
python -m src.utils.db_maintenance --vacuum --analyze

# Optimize for read performance
python -m src.utils.db_maintenance --create-indexes
```

## Monitoring Setup

### System Metrics
1. CPU and memory usage monitoring
2. API response time tracking
3. Strategy performance metrics
4. Error rate monitoring
5. Trade execution latency

### Alerts Configuration
Set up alerts for:
- System failures or high error rates
- API connection issues
- Large portfolio losses
- Risk limit violations
- Unusual AI behavior

## Next Steps

### After Successful Setup
1. **Paper Trading** for at least 1 week
2. **Strategy Backtesting** with historical data
3. **Risk Management** review and adjustment
4. **Performance Analysis** and optimization
5. **Live Trading** with small positions

### Advanced Features
1. **Custom Strategies**: Develop your own trading algorithms
2. **AI Training**: Improve model with historical data
3. **Multi-Asset Trading**: Expand beyond Bank Nifty
4. **Portfolio Optimization**: Advanced allocation strategies
5. **Risk Analytics**: Sophisticated risk modeling

### Community and Support
- Documentation: `docs/` folder
- API Reference: `http://localhost:8000/docs` (when running)
- WebSocket Docs: `specs/001-create-a-comprehensive/contracts/websocket-api.md`
- Issues: GitHub repository issues section

---

**⚠️ Risk Disclaimer**: Trading involves significant risk. Never invest more than you can afford to lose. The NIRAJ system is provided as-is without warranties. Users are responsible for their trading decisions and compliance with applicable regulations.

**🚀 Ready to Trade**: If all systems show green in the dashboard, you're ready to start with paper trading. Good luck!
