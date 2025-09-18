# Quick Start Guide: NIRAJ Algorithmic Trading System

**Version**: 1.0.0  
**Date**: 17 September 2025  
**Target Audience**: Developers and traders  
**Estimated Setup Time**: 30 minutes

## Prerequisites

### System Requirements
- **OS**: Ubuntu 22.04 LTS or compatible Linux distribution
- **Python**: 3.11 or higher
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 50GB free space for data and models
- **Network**: Stable internet connection (for API calls and data feeds)

### Required Accounts
- **Angel One Trading Account**: For primary broker integration
- **Dhan Trading Account**: For secondary broker integration (optional)
- **News API Key**: For news sentiment analysis
- **Weather API Key**: For weather impact analysis (optional)

### Development Tools
- **VS Code**: Recommended IDE with Python extensions
- **Git**: Version control
- **Poetry**: Python dependency management
- **Docker**: For containerized deployment (optional)

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/Pusparaj99op/NIRAJ.git
cd NIRAJ
```

### 2. Install Python Dependencies
```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 3. Install Ollama and AI Model
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Gemma3 model
ollama pull gemma3:4b-it-q4_K_M

# Verify installation
ollama list
```

### 4. Configure Environment
```bash
# Copy environment template
cp config/trading_config.yml.example config/trading_config.yml
cp config/api_config.yml.example config/api_config.yml
cp config/ai_config.yml.example config/ai_config.yml
```

## Configuration

### Trading Configuration
Edit `config/trading_config.yml`:

```yaml
trading:
  mode: paper  # Change to 'real' for live trading
  capital: 100000  # Virtual capital for paper trading
  max_risk_per_trade: 0.02  # 2% max risk per trade
  max_daily_loss: 0.05  # 5% max daily loss
  pin: "1937"  # PIN for real trading mode

symbols:
  primary: "BANKNIFTY"
  secondary:
    - "HDFCBANK"
    - "ICICIBANK"
    - "KOTAKBANK"
    - "AXISBANK"
    - "INDUSINDBK"
    - "IDFCFIRSTB"
    - "FEDERALBNK"
    - "AUBANK"
    - "SBIN"
    - "PNB"
    - "BANKBARODA"
    - "CANBK"

strategies:
  enabled:
    - "predator_strategy"
    - "time_arbitrage"
    - "fear_exploiter"
    - "black_swan_hunter"
  confidence_threshold: 0.7
```

### API Configuration
Edit `config/api_config.yml`:

```yaml
angel_one:
  api_key: "your_angel_one_api_key"
  api_secret: "your_angel_one_api_secret"
  totp_secret: "your_totp_secret"  # For 2FA

dhan:
  api_key: "your_dhan_api_key"
  api_secret: "your_dhan_api_secret"

news_api:
  key: "your_news_api_key"

weather_api:
  key: "your_weather_api_key"
```

### AI Configuration
Edit `config/ai_config.yml`:

```yaml
ollama:
  model: "gemma3:4b-it-q4_K_M"
  host: "http://localhost:11434"
  timeout: 30
  confidence_threshold: 0.7

rag:
  chunk_size: 1000
  overlap: 200
  top_k: 5

learning:
  adaptation_rate: 0.1
  memory_size: 10000
  feedback_window: 100
```

## Database Setup

### Initialize SQLite Database
```bash
# Run database initialization
python -m niraj.core.data_manager --init-db

# Verify database creation
ls -la data/
```

### Initial Data Load
```bash
# Download historical data for Bank Nifty
python -m niraj.core.data_manager --download-historical --symbol BANKNIFTY --days 365

# Download data for individual banks
python -m niraj.core.data_manager --download-historical --symbol HDFCBANK --days 365
python -m niraj.core.data_manager --download-historical --symbol ICICIBANK --days 365
# ... repeat for other banks
```

## Running the System

### 1. Start Core Services
```bash
# Terminal 1: Start data manager
python -m niraj.core.data_manager

# Terminal 2: Start information processor
python -m niraj.core.information_processor

# Terminal 3: Start analysis engine
python -m niraj.core.analysis_engine

# Terminal 4: Start execution engine
python -m niraj.core.execution_engine
```

### 2. Start AI Services
```bash
# Terminal 5: Start AI integration
python -m niraj.ai.gemma3_integration

# Terminal 6: Start RAG processor
python -m niraj.ai.rag_processor
```

### 3. Start API Server
```bash
# Terminal 7: Start FastAPI server
uvicorn niraj.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start Frontend (Optional)
```bash
# Terminal 8: Start React frontend
cd frontend
npm install
npm start
```

## Verification Tests

### 1. API Health Check
```bash
curl http://localhost:8000/api/v1/system/status
```

Expected response:
```json
{
  "status": "HEALTHY",
  "uptime": 300,
  "active_strategies": 4,
  "ai_model_status": "READY"
}
```

### 2. Market Data Test
```bash
curl "http://localhost:8000/api/v1/market-data?symbol=BANKNIFTY&limit=5"
```

### 3. Strategy Test
```bash
curl http://localhost:8000/api/v1/strategies
```

### 4. AI Analysis Test
```bash
curl -X POST http://localhost:8000/api/v1/ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"context": "Test market analysis", "strategy_type": "PREDATORY"}'
```

## Paper Trading Mode

### Start Paper Trading
The system starts in paper trading mode by default with ₹1,00,000 virtual capital.

### Monitor Performance
```bash
# Check portfolio status
curl http://localhost:8000/api/v1/portfolio

# View recent trades
curl http://localhost:8000/api/v1/trades?limit=10

# Check strategy performance
curl http://localhost:8000/api/v1/strategies
```

### Access Web Interface
- Open browser to `http://localhost:3000`
- Dashboard shows real-time P&L, active strategies, and AI insights
- Monitor strategy confidence scores and execution signals

## Real Trading Mode

⚠️ **WARNING**: Real trading involves financial risk. Ensure proper testing in paper mode first.

### Switch to Real Trading
```bash
# Update configuration
sed -i 's/mode: paper/mode: real/' config/trading_config.yml

# Restart services
# Kill all running processes and restart with new configuration
```

### Authentication
```bash
# Authenticate with PIN
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"pin": "1937"}'
```

### Monitor Real Trades
```bash
# Watch trade executions in real-time
curl http://localhost:8000/api/v1/trades?status=EXECUTED
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed
```bash
# Check Ollama status
ollama list

# Restart Ollama service
sudo systemctl restart ollama

# Verify model is loaded
ollama show gemma3:4b-it-q4_K_M
```

#### 2. API Rate Limits
```bash
# Check API status
curl http://localhost:8000/api/v1/system/status

# View rate limit headers in broker API responses
# Implement exponential backoff in configuration
```

#### 3. Database Connection Issues
```bash
# Check database file
ls -la data/niraj.db

# Verify permissions
chmod 644 data/niraj.db

# Reinitialize if corrupted
rm data/niraj.db
python -m niraj.core.data_manager --init-db
```

#### 4. Memory Issues
```bash
# Monitor memory usage
htop

# Adjust Python memory limits
export PYTHONMALLOC=jemalloc

# Reduce data retention in configuration
```

### Logs and Debugging

#### View Application Logs
```bash
# System logs
tail -f logs/system.log

# Trade logs
tail -f logs/trades.log

# AI logs
tail -f logs/ai.log
```

#### Enable Debug Mode
```bash
# Set debug logging
export LOG_LEVEL=DEBUG

# Restart services with debug output
```

### Performance Optimization

#### 1. Database Optimization
```bash
# Create database indexes
python -m niraj.core.data_manager --optimize-db

# Enable WAL mode
python -m niraj.core.data_manager --enable-wal
```

#### 2. Memory Tuning
```bash
# Adjust Python GC
export PYTHONGC=0  # Disable automatic GC
export PYTHONMALLOC=malloc  # Use system malloc
```

#### 3. Network Optimization
```bash
# Use connection pooling
# Configure keep-alive for API connections
# Implement request batching
```

## Next Steps

### Advanced Configuration
1. **Strategy Tuning**: Adjust confidence thresholds and risk parameters
2. **Custom Strategies**: Implement additional trading strategies
3. **Backtesting**: Run historical backtests on your strategies
4. **Risk Management**: Configure advanced risk management rules

### Production Deployment
1. **Containerization**: Use Docker for consistent deployment
2. **Monitoring**: Set up application monitoring and alerting
3. **Backup**: Configure automated data backups
4. **Security**: Implement additional security measures

### Development
1. **Testing**: Write comprehensive unit and integration tests
2. **Documentation**: Update documentation for custom modifications
3. **Performance**: Profile and optimize critical code paths
4. **Scaling**: Design for horizontal scaling if needed

## Support

### Documentation
- **API Docs**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Code Documentation**: Check docstrings in source code
- **Configuration Guide**: Refer to `docs/configuration.md`

### Community
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Join community discussions
- **Wiki**: Comprehensive guides and tutorials

### Emergency Contacts
- **System Issues**: Check logs and restart services
- **Trading Issues**: Switch to paper trading mode immediately
- **Data Issues**: Restore from backups if available

---

**Remember**: Always start with paper trading to validate your strategies before risking real capital. Happy trading! 🚀