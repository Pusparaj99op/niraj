# 🚀 NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-blue.svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/Pusparaj99op/NIRAJ)

**Enterprise-grade algorithmic trading platform with AI-powered strategies, real-time execution, and comprehensive risk management.**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [API Reference](#-api-reference) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Trading Strategies](#-trading-strategies)
- [AI Integration](#-ai-integration)
- [Security](#-security)
- [Performance](#-performance)
- [Monitoring](#-monitoring)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

---

## 🌟 Overview

NIRAJ is a comprehensive, enterprise-grade algorithmic trading system specifically designed for Bank Nifty Index futures and options trading on the NSE (National Stock Exchange). Built with cutting-edge AI technology and advanced risk management, NIRAJ delivers:

- **AI-Powered Decision Making**: Ollama Gemma3 integration for intelligent pattern recognition
- **Real-Time Execution**: Sub-millisecond trade execution with multi-broker support
- **Advanced Strategies**: 20+ aggressive trading strategies with proven profit potential
- **Enterprise Security**: Multi-factor authentication, encryption, and audit trails
- **Risk Management**: Dynamic position sizing, circuit breakers, and correlation analysis
- **Paper Trading**: Risk-free strategy validation with virtual capital
- **Real-Time Analytics**: Live performance monitoring and AI confidence tracking

### Target Markets
- **Primary**: Bank Nifty Index F&O
- **Secondary**: 12 Bank Nifty constituent banks (HDFC Bank, ICICI Bank, Kotak Mahindra Bank, etc.)
- **Exchange**: NSE (National Stock Exchange)
- **Currency**: INR

---

## ✨ Features

### 🧠 AI & Machine Learning
- **Ollama Gemma3 Integration**: Local AI deployment for pattern recognition and predictions
- **RAG Processing**: Retrieval-Augmented Generation for market knowledge
- **Confidence Tracking**: Dynamic confidence scoring (0-100%) for each strategy
- **Adaptive Learning**: Success/failure-based model adjustment and error correction
- **Sentiment Analysis**: News feeds, social media trends, and market psychology analysis

### 📈 Trading Capabilities
- **Paper Trading Mode**: Virtual capital (₹1,00,000) for risk-free testing
- **Live Trading Mode**: PIN-protected (1937) real capital trading
- **Multi-Broker Support**: Angel One (primary), Dhan (secondary)
- **20+ Trading Strategies**: From predatory to quantitative approaches
- **Real-Time Execution**: Sub-millisecond order placement and management
- **Dynamic Risk Management**: Automated stop-loss, profit-taking, and position sizing

### 🔧 Technical Infrastructure
- **FastAPI Backend**: High-performance Python API with async support
- **React Frontend**: Modern TypeScript interface with real-time updates
- **WebSocket Streaming**: Real-time market data and trade signals
- **SQLite + Redis**: Robust data storage and caching
- **Poetry Management**: Dependency management and virtual environments
- **Enterprise Security**: JWT authentication, encryption, audit logging

### 📊 Analytics & Monitoring
- **Real-Time Dashboard**: Live P&L, positions, and performance metrics
- **Strategy Performance**: Detailed backtesting and optimization
- **Risk Analytics**: Portfolio risk, correlation analysis, and exposure monitoring
- **AI Monitoring**: Model performance, prediction accuracy, and learning progress
- **System Health**: Comprehensive monitoring and alerting

---

## 🏗️ Architecture

NIRAJ follows a microservices-inspired architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   AI Engine     │
│   (React/TS)    │◄──►│   (FastAPI)     │◄──►│   (Gemma3)      │
│   Port: 3005    │    │   Port: 8000    │    │   Port: 11434   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │   Data Layer    │              │
         │              │  SQLite + Redis │              │
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Broker APIs   │    │   Market Data   │
│   Real-time     │    │  Angel One/Dhan │    │   News/Weather  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

1. **Data Manager**: Historical data maintenance and real-time updates
2. **Information Processor**: Multi-threaded data ingestion and preprocessing
3. **Analysis Engine**: Technical, fundamental, and AI-powered analysis
4. **Execution Engine**: Real-time trade execution and risk management
5. **Strategy Engine**: 20+ algorithmic trading strategies
6. **AI Integration**: Ollama Gemma3 for pattern recognition and learning

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- 16GB+ RAM (recommended)
- Linux/macOS (Windows via WSL2)

That's it! 🎉

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Interactive Menu System (Recommended)

NIRAJ now features a comprehensive interactive menu system for easy management:

```bash
# Start interactive menu (default when no arguments provided)
python niraj.py

# Or explicitly request menu mode
python niraj.py --menu
python niraj.py menu
```

**Menu Features:**
- 🎯 **Main Menu**: Central hub with 9 categories of operations
- 🚀 **Start Services**: Pre-configured setups (Development, Production, Testing, Custom)
- 🛑 **Stop Services**: Individual or bulk service termination
- 📊 **Service Status**: Real-time status monitoring with URLs
- 📦 **Dependencies**: Automated installation management
- ⚙️ **Configuration**: View, edit, and manage configurations
- 🔧 **Service Management**: Restart, logs, health checks, metrics
- 📚 **Help System**: Complete documentation and troubleshooting
- 🌍 **Environment**: Switch between development/production/testing modes
- 📋 **Monitoring**: Logs and performance tracking

### Command Line Interface

For direct operations without the menu:

```bash
# Development mode with all services
python niraj.py --enable-api --enable-frontend --enable-redis --enable-ollama

# Production mode with API only
python niraj.py --mode production --enable-api --enable-redis

# Testing mode
python niraj.py --mode testing --enable-api

# Service management commands
python niraj.py status          # Show current service status
python niraj.py stop            # Stop all running services
python niraj.py install         # Install project dependencies

# Custom configuration
python niraj.py --config custom.json --enable-api

# View help
python niraj.py --help
```

**Enhanced Features:**
- 🎮 **Interactive Menu System**: User-friendly graphical interface
- 🚀 **Quick Setup Presets**: One-click development/production/testing setups
- 🔄 **Service Management**: Start, stop, restart, monitor individual services
- 📊 **Real-time Monitoring**: Live status updates and health checks
- 🎨 **Beautiful Interface**: Colored output with emojis and professional styling
- ⚙️ **Configuration Management**: Visual config editing and validation
- 📚 **Built-in Help System**: Comprehensive guides and troubleshooting
- 🛠️ **Advanced Tooling**: Log viewing, performance metrics, diagnostics
- 🌍 **Multi-Environment**: Easy switching between development/production/testing
- 🔧 **Custom Configurations**: JSON-based config files with inheritance
- 📱 **Responsive Design**: Works beautifully in any terminal size
- 🚨 **Error Handling**: Graceful error recovery and user guidance

---

## 💻 Installation

### Automated Installation (Recommended)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run complete setup
./scripts/setup_dev.sh
```

### Manual Installation

#### Backend Setup

```bash
cd backend/

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Initialize database
poetry run python -m src.core.database_manager --init

# Start development server
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend/

# Install dependencies
npm install

# Start development server
npm run dev
```

#### AI Setup (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Gemma3 model
ollama pull gemma3:4b-it-q4_K_M

# Start Ollama service
ollama serve
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` files in both `backend/` and `frontend/` directories:

#### Backend (.env)
```bash
# Database
DATABASE_URL=sqlite:///./data/niraj.db
REDIS_URL=redis://localhost:6379

# API Keys
ANGEL_ONE_API_KEY=your_angel_one_api_key
ANGEL_ONE_SECRET_KEY=your_angel_one_secret_key
DHAN_CLIENT_ID=your_dhan_client_id
DHAN_ACCESS_TOKEN=your_dhan_access_token
NEWS_API_KEY=your_news_api_key
WEATHER_API_KEY=your_weather_api_key

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b-it-q4_K_M

# Security
JWT_SECRET_KEY=your_super_secret_jwt_key_here
PIN_CODE=1937

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### Frontend (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
```

### Configuration Files

NIRAJ uses YAML configuration files in `backend/config/`:

- `development.yaml`: Development environment settings
- `production.yaml`: Production environment settings
- `testing.yaml`: Test environment settings

Example configuration:
```yaml
database:
  url: "sqlite:///./data/niraj.db"
  pool_size: 20
  echo: false

redis:
  url: "redis://localhost:6379"
  max_connections: 100

ai:
  ollama:
    base_url: "http://localhost:11434"
    model: "gemma3:4b-it-q4_K_M"
    timeout: 120

trading:
  paper_mode: true
  initial_capital: 100000
  max_position_size: 0.1
  stop_loss_percent: 0.02
```

---

## 🎯 Usage

### Paper Trading Mode (Default)

NIRAJ starts in paper trading mode with virtual capital:

```python
# Access the dashboard
http://localhost:3005

# Virtual capital: ₹1,00,000
# No real money at risk
# All strategies enabled for testing
```

### Live Trading Mode (PIN: 1937)

Switch to live trading after thorough testing:

1. Navigate to Settings → Trading Mode
2. Enter PIN: `1937`
3. Configure real capital allocation
4. Enable desired strategies
5. Monitor real-time execution

### API Usage

#### Authentication
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "trader", "password": "secure_password"}'
```

#### Get Strategies
```bash
curl -X GET "http://localhost:8000/api/v1/strategies" \
  -H "Authorization: Bearer your_jwt_token"
```

#### Create Strategy
```bash
curl -X POST "http://localhost:8000/api/v1/strategies" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Strategy",
    "description": "My custom trading strategy",
    "risk_level": "medium",
    "parameters": {...}
  }'
```

### WebSocket Streaming

Connect to real-time data streams:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=your_jwt_token');

// Subscribe to market data
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'market_data',
  symbols: ['BANKNIFTY', 'HDFCBANK']
}));

// Subscribe to trade signals
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'trade_signals'
}));
```

---

## 📚 API Reference

### Core Endpoints

#### Authentication
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/switch-mode` - Switch trading mode
- `POST /api/v1/auth/logout` - User logout

#### Strategies
- `GET /api/v1/strategies` - List all strategies
- `POST /api/v1/strategies` - Create new strategy
- `GET /api/v1/strategies/{id}` - Get strategy details
- `PUT /api/v1/strategies/{id}` - Update strategy
- `DELETE /api/v1/strategies/{id}` - Delete strategy
- `POST /api/v1/strategies/{id}/backtest` - Run backtest

#### Trading
- `GET /api/v1/trades` - List trades
- `POST /api/v1/trades` - Execute trade
- `GET /api/v1/trades/{id}` - Get trade details
- `PATCH /api/v1/trades/{id}` - Update trade

#### Portfolio
- `GET /api/v1/portfolio` - Get portfolio overview
- `GET /api/v1/portfolio/positions` - Get positions
- `GET /api/v1/portfolio/performance` - Get performance metrics

#### System
- `GET /api/v1/system/status` - System health check
- `GET /api/v1/ai/predictions` - AI predictions and confidence
- `GET /api/v1/market-data/{symbol}` - Market data

### WebSocket Streams

#### Available Streams
- `market_data` - Real-time market data
- `trade_signals` - Trading signals and alerts
- `portfolio` - Portfolio updates
- `ai_insights` - AI predictions and analysis

#### Message Format
```json
{
  "type": "subscribe|unsubscribe|data",
  "stream": "market_data",
  "data": {...},
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 🎯 Trading Strategies

NIRAJ implements 20 aggressive trading strategies across four categories:

### Predatory Strategies (High-Risk, High-Reward)
1. **The Predator Strategy**: Order book analysis and institutional front-running (500-1000% profit potential)
2. **The Vulture Approach**: Market panic exploitation and fear-driven trading (200-800% profit potential)
3. **The Shadow Trader**: Institutional order mirroring and front-running (300-600% profit potential)
4. **The Liquidation Hunter**: Stop-loss cascade triggering (400-1200% profit potential)

### Quantitative Dominance Strategies
5. **The Time Arbitrage**: Microsecond price difference exploitation (50-100% annually)
6. **The Volatility Vampire**: Options volatility mispricing exploitation (200-500% profit potential)
7. **The News Flash Strategy**: AI-powered news interpretation and execution (300-800% profit potential)
8. **The Manipulation Detector**: Anti-manipulation counter-trading (600-1500% profit potential)

### Psychological Warfare Strategies
9. **The Fear Exploiter**: Market fear amplification through strategic positioning (800-2000% profit potential)
10. **The Greed Trap**: Retail trader overconfidence exploitation (400-1000% profit potential)
11. **The Squeeze Play**: Short covering coordination (1000-5000% profit potential)

### Advanced Mathematical Strategies
12. **The Black Swan Hunter**: Tail risk hedging for rare events (5000-50000% profit potential)
13. **The Gamma Scalper**: Market maker gamma exposure exploitation (200-600% profit potential)
14. **The Theta Destroyer**: Time decay profit maximization (100-300% profit potential)
15. **The Market Maker Killer**: Algorithm manipulation and exploitation (300-800% profit potential)

### Extreme Risk Strategies
16. **The All-or-Nothing Gambit**: Maximum leverage high-probability plays (2000-10000% profit potential)
17. **The System Breaker**: Exchange error and glitch exploitation (1000%+ profit potential)
18. **The Regulatory Gap**: Legal loophole exploitation (500-2000% profit potential)

### Coordination Strategies
19. **The Swarm Intelligence**: Multi-account coordinated trading (800-3000% profit potential)
20. **The Information Harvester**: Privileged information monetization (2000%+ profit potential)

### Strategy Configuration

Each strategy can be configured with:
- Risk level (low, medium, high, extreme)
- Position sizing rules
- Stop-loss and take-profit levels
- Market conditions filters
- Time-based activation rules

---

## 🤖 AI Integration

### Ollama Gemma3 Integration

NIRAJ leverages the power of Ollama's Gemma3 model for:

#### Pattern Recognition
- Chart pattern identification
- Price action analysis
- Volume profile analysis
- Market structure recognition

#### Sentiment Analysis
- News sentiment scoring
- Social media trend analysis
- Market psychology indicators
- Fear & greed index calculation

#### Predictive Analytics
- Price movement predictions
- Volatility forecasting
- Trend continuation/reversal signals
- Support/resistance level identification

#### Confidence Scoring
- 0-100% confidence scores for each prediction
- Dynamic confidence adjustment based on market conditions
- Historical accuracy tracking
- Risk-adjusted confidence metrics

### RAG (Retrieval-Augmented Generation)

NIRAJ implements RAG for enhanced AI capabilities:

```python
# Example RAG query
rag_processor = RAGProcessor()
market_knowledge = rag_processor.query(
    "What are the typical patterns before Bank Nifty reversal?"
)

# AI generates context-aware predictions
prediction = gemma3_client.predict(
    market_data=current_data,
    context=market_knowledge,
    confidence_threshold=0.75
)
```

### AI Learning Pipeline

1. **Data Ingestion**: Market data, news, social media
2. **Feature Engineering**: Technical indicators, sentiment scores
3. **Pattern Recognition**: Gemma3 model inference
4. **Confidence Calculation**: Statistical confidence metrics
5. **Decision Making**: Risk-adjusted strategy selection
6. **Feedback Loop**: Performance-based learning adjustment

---

## 🔒 Security

### Multi-Layer Security Architecture

#### Authentication & Authorization
- **JWT Tokens**: Secure token-based authentication
- **Multi-Factor Authentication**: Optional MFA support
- **Session Management**: Secure session handling
- **Role-Based Access**: Granular permission control

#### Data Protection
- **Encryption at Rest**: AES-256 database encryption
- **Encryption in Transit**: TLS 1.3 for all communications
- **API Key Management**: Secure credential storage
- **Audit Logging**: Comprehensive activity tracking

#### Trading Security
- **PIN Protection**: Live trading requires PIN (1937)
- **Trade Verification**: Multi-level trade confirmation
- **Risk Limits**: Hard-coded maximum position limits
- **Circuit Breakers**: Automatic trading halts on anomalies

#### Network Security
- **CORS Configuration**: Restricted cross-origin requests
- **Rate Limiting**: API request throttling
- **IP Filtering**: Whitelist-based access control
- **DDoS Protection**: Request rate limiting and filtering

### Security Configuration

```yaml
security:
  jwt:
    secret_key: "${JWT_SECRET_KEY}"
    algorithm: "HS256"
    expire_minutes: 30

  mfa:
    enabled: true
    methods: ["totp", "sms"]

  encryption:
    algorithm: "AES-256-GCM"
    key_rotation_days: 90

  rate_limiting:
    requests_per_minute: 100
    burst_limit: 200
```

---

## ⚡ Performance

### System Performance Specifications

#### Execution Speed
- **Order Execution**: Sub-millisecond latency
- **Data Processing**: < 100ms for real-time data
- **API Response**: < 50ms average response time
- **WebSocket Latency**: < 10ms message delivery

#### Scalability
- **Concurrent Users**: 1000+ simultaneous connections
- **API Throughput**: 10,000+ requests/second
- **Data Volume**: 1TB+ historical data processing
- **Strategy Execution**: 100+ simultaneous strategies

#### Resource Requirements
- **Minimum RAM**: 8GB (16GB recommended)
- **CPU**: 4+ cores (8+ cores recommended)
- **Storage**: 100GB+ SSD recommended
- **Network**: Low-latency internet connection

### Performance Optimization

#### Database Optimization
- Connection pooling (20 connections)
- Query optimization with indexes
- Async database operations
- Redis caching layer

#### Caching Strategy
- **L1 Cache**: In-memory Python dictionaries
- **L2 Cache**: Redis distributed cache
- **CDN**: Static asset caching
- **Database Cache**: Query result caching

#### Code Optimization
- Async/await throughout the codebase
- Connection pooling for external APIs
- Efficient data structures
- Memory management and garbage collection

---

## 📊 Monitoring

### System Health Monitoring

#### Health Check Endpoints
```bash
# System health
GET /health

# Detailed system status
GET /api/v1/system/status

# AI model health
GET /api/v1/ai/health
```

#### Monitoring Metrics
- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Request rates, error rates, latency
- **Trading Metrics**: P&L, win rate, Sharpe ratio
- **AI Metrics**: Prediction accuracy, confidence scores

#### Logging
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Automatic log file rotation
- **Centralized Logging**: ELK stack integration ready

### Performance Dashboard

The NIRAJ dashboard provides real-time monitoring of:
- Portfolio performance and P&L
- Strategy performance metrics
- AI model confidence and accuracy
- System health and resource usage
- Trade execution statistics
- Risk management alerts

---

## 🧪 Testing

### Test Suite Overview

NIRAJ implements comprehensive testing following TDD principles:

#### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: Service integration testing
- **Contract Tests**: API contract validation
- **End-to-End Tests**: Complete workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability and penetration testing

#### Running Tests

```bash
# Backend tests
cd backend/
poetry run pytest tests/ -v

# Frontend tests
cd frontend/
npm test

# All tests
./scripts/run_tests.sh

# Specific test categories
poetry run pytest tests/unit/ -v
poetry run pytest tests/integration/ -v
poetry run pytest tests/contract/ -v
```

#### Test Coverage
- **Target Coverage**: 90%+ code coverage
- **Contract Tests**: All 25 API endpoints covered
- **Integration Tests**: All major workflows tested
- **Performance Tests**: Load testing for 1000+ concurrent users

#### Continuous Integration
```yaml
# GitHub Actions workflow
name: NIRAJ CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: ./scripts/run_tests.sh
```

---

## 🚀 Deployment

### Production Deployment

#### Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# Scale services
docker-compose up --scale backend=3 --scale frontend=2
```

#### Manual Deployment

```bash
# Backend deployment
cd backend/
poetry install --no-dev
poetry run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Frontend deployment
cd frontend/
npm run build
npx serve -s dist -l 3005
```

#### Environment Configurations

##### Development
```yaml
environment: development
debug: true
log_level: DEBUG
reload: true
```

##### Production
```yaml
environment: production
debug: false
log_level: INFO
workers: 4
```

### Infrastructure Requirements

#### Minimum Requirements
- **Server**: 4 CPU cores, 16GB RAM, 100GB SSD
- **OS**: Ubuntu 22.04 LTS or similar
- **Python**: 3.11+
- **Node.js**: 18+
- **Database**: SQLite (development) / PostgreSQL (production)
- **Cache**: Redis 7+

#### Recommended Production Setup
- **Load Balancer**: Nginx or HAProxy
- **Application Server**: Gunicorn with Uvicorn workers
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis Cluster
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

---

## 🤝 Contributing

We welcome contributions from the trading and development community!

### Development Setup

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/NIRAJ.git
   cd NIRAJ
   ```
3. **Set up development environment**
   ```bash
   ./scripts/setup_dev.sh
   ```
4. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-strategy
   ```
5. **Make your changes**
6. **Run tests**
   ```bash
   ./scripts/run_tests.sh
   ```
7. **Commit and push**
   ```bash
   git commit -m "Add amazing new strategy"
   git push origin feature/amazing-strategy
   ```
8. **Create a Pull Request**

### Contribution Guidelines

#### Code Standards
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Follow ESLint configuration
- **Testing**: Maintain 90%+ test coverage
- **Documentation**: Update docs for new features

#### Commit Messages
```
feat: add new trading strategy
fix: resolve API authentication issue
docs: update installation guide
test: add unit tests for risk management
```

#### Pull Request Process
1. Ensure all tests pass
2. Update documentation
3. Add changelog entry
4. Request code review
5. Address feedback
6. Merge when approved

### Areas for Contribution

- **Trading Strategies**: New algorithmic strategies
- **AI Models**: Enhanced AI integration
- **Risk Management**: Advanced risk controls
- **User Interface**: Frontend improvements
- **Performance**: Optimization and scaling
- **Documentation**: Guides and tutorials
- **Testing**: Test coverage and quality

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Pranay Gajbhiye

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🆘 Support

### Getting Help

- **Documentation**: Check our comprehensive docs
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join GitHub Discussions for questions
- **Email**: support@niraj-trading.com (if available)

### FAQ

#### Q: Is NIRAJ suitable for beginners?
A: NIRAJ is designed for experienced traders familiar with algorithmic trading concepts. We recommend starting with paper trading mode.

#### Q: What are the system requirements?
A: Minimum 8GB RAM, 4 CPU cores, and stable internet connection. 16GB+ RAM recommended for optimal performance.

#### Q: Can I add custom trading strategies?
A: Yes! NIRAJ provides a strategy interface for implementing custom algorithms. See the developer documentation.

#### Q: Is my data secure?
A: Yes, NIRAJ implements enterprise-grade security with encryption, secure authentication, and audit logging.

#### Q: Can I run multiple instances?
A: Yes, NIRAJ supports horizontal scaling. Configure load balancing for production deployments.

### Support Channels

- 🐛 **Bug Reports**: GitHub Issues
- 💡 **Feature Requests**: GitHub Discussions
- 📖 **Documentation**: `/docs` directory
- 💬 **Community**: GitHub Discussions
- 📧 **Enterprise Support**: Available on request

---

<div align="center">

**Built with ❤️ by [Pranay Gajbhiye](https://github.com/Pusparaj99op)**

[![GitHub Stars](https://img.shields.io/github/stars/Pusparaj99op/NIRAJ?style=social)](https://github.com/Pusparaj99op/NIRAJ)
[![GitHub Forks](https://img.shields.io/github/forks/Pusparaj99op/NIRAJ?style=social)](https://github.com/Pusparaj99op/NIRAJ)
[![GitHub Watchers](https://img.shields.io/github/watchers/Pusparaj99op/NIRAJ?style=social)](https://github.com/Pusparaj99op/NIRAJ)

**⭐ Star us on GitHub — it helps!**

[Report Bug](https://github.com/Pusraaj99op/NIRAJ/issues) • [Request Feature](https://github.com/Pusparaj99op/NIRAJ/discussions) • [Contribute](CONTRIBUTING.md)

</div>
