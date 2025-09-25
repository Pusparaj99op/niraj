# NIRAJ System Architecture

## Overview

NIRAJ is a sophisticated, enterprise-grade algorithmic trading system built with a microservices-inspired architecture. The system is designed for high-performance, real-time trading with comprehensive risk management, AI-powered decision making, and enterprise-level security.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 NIRAJ Trading System                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   Frontend      │    │   Load Balancer │    │   API Gateway   │            │
│  │   (React/TS)    │◄──►│   (Nginx/HAProxy)│◄──►│   (FastAPI)     │            │
│  │   Port: 3005    │    │   Port: 80/443  │    │   Port: 8000    │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│           │                       │                       │                    │
│           │                       │                       ▼                    │
│           │              ┌─────────────────────────────────────────┐           │
│           │              │          Core Services Layer           │           │
│           │              ├─────────────────────────────────────────┤           │
│           │              │                                         │           │
│           │              │  ┌─────────────────┐ ┌─────────────────┐│           │
│           │              │  │ Auth Service    │ │ Config Service  ││           │
│           │              │  │ - JWT Tokens    │ │ - YAML Configs  ││           │
│           │              │  │ - MFA Support   │ │ - Env Variables ││           │
│           │              │  │ - Session Mgmt  │ │ - Hot Reload    ││           │
│           │              │  └─────────────────┘ └─────────────────┘│           │
│           │              │                                         │           │
│           │              │  ┌─────────────────┐ ┌─────────────────┐│           │
│           │              │  │ User Service    │ │ Audit Service   ││           │
│           │              │  │ - User Mgmt     │ │ - Activity Log  ││           │
│           │              │  │ - Preferences   │ │ - Compliance    ││           │
│           │              │  │ - Permissions   │ │ - Forensics     ││           │
│           │              │  └─────────────────┘ └─────────────────┘│           │
│           │              └─────────────────────────────────────────┘           │
│           │                                 │                                  │
│           ▼                                 ▼                                  │
│  ┌─────────────────┐              ┌─────────────────┐                         │
│  │   WebSocket     │              │   Data Layer    │                         │
│  │   Server        │              │                 │                         │
│  │   - Real-time   │              │  ┌─────────────┐│                         │
│  │   - Multi-stream│              │  │ SQLite/     ││                         │
│  │   - Connection  │              │  │ PostgreSQL  ││                         │
│  │     pooling     │              │  │ - Trades    ││                         │
│  │   - Message     │              │  │ - Portfolio ││                         │
│  │     batching    │              │  │ - Users     ││                         │
│  └─────────────────┘              │  │ - Strategies││                         │
│                                   │  │ - Market    ││                         │
│                                   │  │   Data      ││                         │
│                                   │  └─────────────┘│                         │
│                                   │                 │                         │
│                                   │  ┌─────────────┐│                         │
│                                   │  │ Redis Cache ││                         │
│                                   │  │ - Sessions  ││                         │
│                                   │  │ - Market    ││                         │
│                                   │  │   Data      ││                         │
│                                   │  │ - AI Results││                         │
│                                   │  │ - Rate      ││                         │
│                                   │  │   Limiting  ││                         │
│                                   │  └─────────────┘│                         │
│                                   └─────────────────┘                         │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              Processing Layer                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │ Data Manager    │    │ Info Processor  │    │ Analysis Engine │           │
│  │ - Historical    │    │ - Multi-threaded│    │ - Technical     │           │
│  │   Data Mgmt     │    │ - Real-time     │    │ - Fundamental   │           │
│  │ - Gap Filling   │    │ - Data Ingestion│    │ - Quantitative  │           │
│  │ - CSV Storage   │    │ - Preprocessing │    │ - Sentiment     │           │
│  │ - 15min/1day    │    │ - Market Events │    │ - 50+ Indicators│           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│           │                       │                       │                   │
│           │                       ▼                       │                   │
│           │              ┌─────────────────┐              │                   │
│           │              │ Risk Management │              │                   │
│           │              │ & Execution     │              │                   │
│           │              │ - Circuit       │              │                   │
│           │              │   Breakers      │              │                   │
│           │              │ - Position      │              │                   │
│           │              │   Sizing        │              │                   │
│           │              │ - Stop Loss     │              │                   │
│           │              │ - Kelly         │              │                   │
│           │              │   Criterion     │              │                   │
│           │              │ - Correlation   │              │                   │
│           │              │   Analysis      │              │                   │
│           │              └─────────────────┘              │                   │
│           │                       │                       │                   │
│           ▼                       ▼                       ▼                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │ Strategy Engine │    │ AI Integration  │    │ Tech Indicators │           │
│  │ - 20 Strategies │    │ - Ollama Gemma3 │    │ - RSI, MACD     │           │
│  │ - Predatory     │    │ - RAG Processor │    │ - Bollinger     │           │
│  │ - Quantitative  │    │ - Confidence    │    │ - Moving Avg    │           │
│  │ - Psychological │    │   Tracking      │    │ - Volume        │           │
│  │ - Mathematical  │    │ - Learning      │    │ - Momentum      │           │
│  │ - Extreme Risk  │    │   Engine        │    │ - Pattern       │           │
│  │ - Coordination  │    │ - Pattern       │    │   Recognition   │           │
│  └─────────────────┘    │   Recognition   │    └─────────────────┘           │
│                         └─────────────────┘                                  │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              External Layer                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │ Broker APIs     │    │ Market Data     │    │ Information     │           │
│  │ - Angel One     │    │ APIs            │    │ Sources         │           │
│  │   Smart API     │    │ - NSE Feed      │    │ - News API      │           │
│  │ - Dhan HQ API   │    │ - Real-time     │    │ - Weather API   │           │
│  │ - Order Mgmt    │    │   Quotes        │    │ - Social Media  │           │
│  │ - Portfolio     │    │ - Historical    │    │ - Economic      │           │
│  │   Sync          │    │   Data          │    │   Indicators    │           │
│  │ - Auto-reauth   │    │ - Options       │    │ - Earnings      │           │
│  │   (12h)         │    │   Chain         │    │   Reports       │           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Security & Monitoring                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │ Security Layer  │    │ Monitoring      │    │ Performance     │           │
│  │ - AES-256       │    │ - System Health │    │ - Sub-ms        │           │
│  │   Encryption    │    │ - API Metrics   │    │   Execution     │           │
│  │ - TLS 1.3       │    │ - Trade         │    │ - Connection    │           │
│  │ - JWT Auth      │    │   Analytics     │    │   Pooling       │           │
│  │ - Rate Limiting │    │ - AI Accuracy   │    │ - Async Ops     │           │
│  │ - Audit Trails  │    │ - Error         │    │ - Memory        │           │
│  │ - IP Filtering  │    │   Tracking      │    │   Management    │           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend Layer (React/TypeScript)

**Purpose**: User interface and experience
**Port**: 3005
**Technology**: React 18, TypeScript, Vite

**Key Components**:
- **Dashboard**: Real-time portfolio overview, P&L tracking
- **AI Monitor**: AI model performance, confidence tracking, predictions
- **Trading Interface**: Order management, market analysis, charting
- **Strategy Performance**: Strategy analytics, backtesting results
- **Risk Management**: Risk controls, position sizing, alerts

**Features**:
- Real-time WebSocket connections
- Responsive design with dark theme
- Interactive charts with Chart.js
- Keyboard shortcuts for traders
- Progressive Web App (PWA) support

### 2. API Gateway (FastAPI)

**Purpose**: Central API management and routing
**Port**: 8000
**Technology**: FastAPI, Python 3.11+, Uvicorn

**Key Features**:
- RESTful API with OpenAPI documentation
- JWT-based authentication
- Rate limiting and throttling
- Request/response validation
- CORS and security middleware
- Health checks and monitoring

**API Categories**:
- Authentication (`/auth/*`)
- Strategy Management (`/strategies/*`)
- Trading Operations (`/trades/*`)
- Portfolio Management (`/portfolio/*`)
- System Status (`/system/*`)
- AI Predictions (`/ai/*`)

### 3. WebSocket Server

**Purpose**: Real-time data streaming
**Technology**: WebSocket with connection pooling

**Streams Available**:
- **Market Data**: Real-time price updates, volume, order book
- **Trade Signals**: AI-generated trading signals and alerts
- **Portfolio Updates**: Position changes, P&L updates
- **AI Insights**: Model predictions, confidence scores, analysis

**Features**:
- Multi-stream subscriptions
- Message batching and compression
- Automatic reconnection with exponential backoff
- Connection pooling and load balancing
- Heartbeat monitoring

### 4. Core Services Layer

#### Authentication Service
- JWT token management
- Multi-factor authentication (MFA)
- Session management and tracking
- Role-based access control (RBAC)
- Device fingerprinting
- Geo-blocking capabilities

#### Configuration Service
- YAML-based configuration management
- Environment-specific settings
- Hot configuration reloading
- Secrets management
- Feature flags

#### User Service
- User profile management
- Trading preferences
- Notification settings
- Audit trail per user

#### Audit Service
- Comprehensive activity logging
- Compliance reporting
- Forensic analysis capabilities
- Data retention policies

### 5. Data Layer

#### Primary Database (SQLite/PostgreSQL)
- **Development**: SQLite for simplicity
- **Production**: PostgreSQL for scalability

**Core Tables**:
- `users`: User accounts and authentication
- `strategies`: Trading strategy definitions
- `trades`: Trade execution records
- `portfolio`: Portfolio positions and performance
- `market_data`: Historical and real-time market data
- `ai_predictions`: AI model predictions and results
- `audit_logs`: System activity and compliance logs
- `configurations`: System configuration settings

#### Cache Layer (Redis)
- **Session Storage**: User sessions and authentication tokens
- **Market Data Cache**: Real-time price data, order book
- **AI Results Cache**: Model predictions and analysis
- **Rate Limiting**: API request throttling
- **Temporary Data**: Processing queues, notifications

### 6. Processing Layer

#### Data Manager
**Purpose**: Historical data management and real-time updates

**Responsibilities**:
- Historical data maintenance (CSV format)
- Automatic gap detection and filling
- Data validation and cleansing
- Multi-timeframe support (15min, 1day)
- Bank-wise data organization

**Data Structure**:
```
/historical_data/
├── BANKNIFTY/
│   ├── 15min/
│   │   ├── BANKNIFTY_15min_2024.csv
│   │   └── BANKNIFTY_15min_2023.csv
│   └── 1day/
│       └── BANKNIFTY_1day.csv
├── HDFCBANK/
└── ICICIBANK/
```

#### Information Processor
**Purpose**: Real-time data ingestion and preprocessing

**Features**:
- Multi-threaded data processing
- Sub-second latency for high-frequency strategies
- Event-driven architecture
- Data normalization and standardization
- Market event detection

**Data Sources**:
- Broker APIs (Angel One, Dhan)
- Market data feeds (NSE)
- News APIs
- Social media sentiment
- Economic indicators

#### Analysis Engine
**Purpose**: Technical, fundamental, and quantitative analysis

**Technical Analysis** (50+ indicators):
- Moving Averages (SMA, EMA, WMA)
- Momentum Indicators (RSI, MACD, Stochastic)
- Volatility Indicators (Bollinger Bands, ATR)
- Volume Indicators (OBV, Volume Profile)
- Chart Patterns (Head & Shoulders, Triangles, Flags)

**Fundamental Analysis**:
- P/E ratios and valuation metrics
- Earnings analysis and forecasts
- Sector health indicators
- Economic data correlation

**Quantitative Analysis**:
- Statistical arbitrage models
- Mean reversion strategies
- Momentum models
- Risk-adjusted returns

### 7. Strategy Engine

**Purpose**: Implementation and execution of 20 trading strategies

#### Strategy Categories:

**Predatory Strategies** (High-Risk, High-Reward):
1. **The Predator Strategy**: Order book analysis, front-running (500-1000%)
2. **The Vulture Approach**: Market panic exploitation (200-800%)
3. **The Shadow Trader**: Institutional mirroring (300-600%)
4. **The Liquidation Hunter**: Stop-loss cascades (400-1200%)

**Quantitative Dominance**:
5. **Time Arbitrage**: Microsecond price differences (50-100%)
6. **Volatility Vampire**: Options mispricing (200-500%)
7. **News Flash Strategy**: AI-powered news trading (300-800%)
8. **Manipulation Detector**: Counter-manipulation (600-1500%)

**Psychological Warfare**:
9. **Fear Exploiter**: Market fear amplification (800-2000%)
10. **Greed Trap**: Retail overconfidence exploitation (400-1000%)
11. **Squeeze Play**: Short covering coordination (1000-5000%)

**Advanced Mathematical**:
12. **Black Swan Hunter**: Tail risk hedging (5000-50000%)
13. **Gamma Scalper**: Market maker exploitation (200-600%)
14. **Theta Destroyer**: Time decay optimization (100-300%)
15. **Market Maker Killer**: Algorithm manipulation (300-800%)

**Extreme Risk**:
16. **All-or-Nothing Gambit**: Maximum leverage plays (2000-10000%)
17. **System Breaker**: Exchange error exploitation (1000%+)
18. **Regulatory Gap**: Legal loophole exploitation (500-2000%)

**Coordination**:
19. **Swarm Intelligence**: Multi-account coordination (800-3000%)
20. **Information Harvester**: Privileged information (2000%+)

### 8. AI Integration Layer

#### Ollama Gemma3 Integration
**Purpose**: AI-powered pattern recognition and prediction

**Model**: Gemma3:4b-it-q4_K_M (local deployment)
**Port**: 11434

**Capabilities**:
- Chart pattern recognition
- Price movement prediction
- Market sentiment analysis
- Risk assessment
- Strategy optimization

#### RAG Processor
**Purpose**: Retrieval-Augmented Generation for market knowledge

**Knowledge Base**:
- Historical market patterns
- Strategy performance data
- News and sentiment analysis
- Economic indicators
- Regulatory information

#### Confidence Tracking System
**Purpose**: Dynamic confidence scoring for AI predictions

**Features**:
- 0-100% confidence scores
- Historical accuracy tracking
- Market condition adjustment
- Risk-adjusted confidence metrics
- Performance feedback loops

#### Learning Engine
**Purpose**: Continuous model improvement and adaptation

**Learning Methods**:
- Success/failure pattern analysis
- Market regime detection
- Strategy performance optimization
- Error correction and adjustment
- Adaptive parameter tuning

### 9. Risk Management & Execution Engine

**Purpose**: Comprehensive risk control and trade execution

#### Risk Management Features:
- **Circuit Breakers**: Automatic trading halts on anomalies
- **Position Sizing**: Dynamic sizing with Kelly Criterion
- **Correlation Analysis**: Cross-asset risk assessment
- **Volatility Checks**: Volatility-based position adjustments
- **Drawdown Limits**: Maximum loss protection
- **Concentration Limits**: Portfolio diversification enforcement

#### Execution Features:
- **Sub-millisecond Execution**: High-frequency trading capability
- **Multi-broker Routing**: Angel One and Dhan integration
- **Order Types**: Market, Limit, Stop, Bracket, Iceberg orders
- **Time-in-Force**: DAY, GTC, IOC, FOK options
- **Smart Order Routing**: Best execution algorithms
- **Partial Fill Handling**: Sophisticated order management

### 10. External Integration Layer

#### Broker APIs
- **Angel One Smart API**: Primary broker integration
- **Dhan HQ API**: Secondary broker for redundancy
- **Auto-reauthentication**: Every 12 hours + startup
- **Order Management**: Real-time order placement and tracking
- **Portfolio Synchronization**: Position and balance updates

#### Market Data APIs
- **NSE Feed**: Real-time market data
- **Historical Data**: OHLCV data with gap filling
- **Options Chain**: Options pricing and Greeks
- **Market Status**: Trading hours and holidays

#### Information Sources
- **News API**: Financial news and analysis
- **Weather API**: Weather-related market impacts
- **Social Media**: Sentiment analysis from Twitter, Reddit
- **Economic Indicators**: GDP, inflation, interest rates

## Data Flow Architecture

### 1. Market Data Flow
```
NSE/Market Data → Broker APIs → Data Manager → Information Processor → Analysis Engine
                                                      ↓
Redis Cache ← WebSocket Server ← Strategy Engine ← AI Integration
     ↓
Frontend Dashboard (Real-time Updates)
```

### 2. Trading Signal Flow
```
Market Analysis → AI Integration → Strategy Engine → Risk Management → Execution Engine
                                                            ↓
                  Audit Service ← Database ← Trade Management ← Broker APIs
                                                            ↓
                              Portfolio Updates → WebSocket → Frontend
```

### 3. AI Prediction Flow
```
Historical Data → RAG Processor → Gemma3 Model → Confidence Tracker → Learning Engine
                                        ↓
                    Strategy Signals ← Prediction Engine ← Pattern Recognition
                            ↓
                    Risk Assessment → Execution Decision → Trade Placement
```

## Scalability Architecture

### Horizontal Scaling
- **Load Balancer**: Nginx/HAProxy for traffic distribution
- **API Gateway Clustering**: Multiple FastAPI instances
- **Database Sharding**: Partitioned data across instances
- **Cache Clustering**: Redis Cluster for distributed caching
- **WebSocket Scaling**: Connection pooling and load balancing

### Vertical Scaling
- **Multi-core Processing**: Async/await throughout
- **Memory Optimization**: Efficient data structures
- **Connection Pooling**: Database and API connections
- **Caching Strategy**: Multi-level caching (L1, L2, CDN)

### Performance Targets
- **API Response Time**: < 50ms average
- **WebSocket Latency**: < 10ms message delivery
- **Trade Execution**: Sub-millisecond for HFT strategies
- **Data Processing**: < 100ms for real-time analysis
- **Concurrent Users**: 1000+ simultaneous connections
- **Throughput**: 10,000+ API requests/second

## Security Architecture

### Multi-Layer Security

#### Application Security
- **JWT Authentication**: Secure token-based auth
- **Multi-Factor Authentication**: TOTP/SMS support
- **Role-Based Access Control**: Granular permissions
- **Session Management**: Secure session handling
- **Input Validation**: Comprehensive request validation

#### Data Security
- **Encryption at Rest**: AES-256 database encryption
- **Encryption in Transit**: TLS 1.3 for all communications
- **Key Management**: Secure credential storage
- **Data Masking**: Sensitive data protection
- **Backup Encryption**: Encrypted backup storage

#### Network Security
- **CORS Configuration**: Restricted cross-origin requests
- **Rate Limiting**: API request throttling
- **IP Filtering**: Whitelist-based access control
- **DDoS Protection**: Request rate limiting
- **Firewall Rules**: Network-level protection

#### Trading Security
- **PIN Protection**: Live trading requires PIN (1937)
- **Trade Verification**: Multi-level confirmation
- **Risk Limits**: Hard-coded maximum positions
- **Circuit Breakers**: Automatic trading halts
- **Audit Trail**: Complete transaction logging

## Monitoring & Observability

### System Monitoring
- **Health Checks**: Automated system health monitoring
- **Performance Metrics**: CPU, memory, disk, network usage
- **API Metrics**: Request rates, error rates, latency
- **Database Monitoring**: Connection pools, query performance
- **Cache Monitoring**: Hit rates, memory usage

### Application Monitoring
- **Trading Metrics**: P&L, win rates, strategy performance
- **AI Metrics**: Prediction accuracy, confidence scores
- **User Metrics**: Active users, session duration
- **Error Tracking**: Exception monitoring and alerting
- **Business Metrics**: Trading volume, commission costs

### Logging Strategy
- **Structured Logging**: JSON-formatted logs
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Centralized Logging**: ELK stack integration
- **Log Rotation**: Automatic log file management
- **Audit Logging**: Compliance and forensic logs

### Alerting
- **System Alerts**: Infrastructure issues, service outages
- **Trading Alerts**: Risk breaches, execution failures
- **AI Alerts**: Model performance degradation
- **Security Alerts**: Authentication failures, suspicious activity
- **Business Alerts**: Performance thresholds, compliance issues

## Disaster Recovery & High Availability

### High Availability
- **Load Balancing**: Traffic distribution across instances
- **Database Replication**: Master-slave configuration
- **Cache Redundancy**: Redis Cluster for fault tolerance
- **Service Redundancy**: Multiple instances of critical services
- **Health Monitoring**: Automatic failover on service failure

### Backup Strategy
- **Database Backups**: Automated daily backups
- **Configuration Backups**: System settings and strategies
- **Code Repository**: Git-based version control
- **Encryption**: All backups encrypted at rest
- **Retention Policy**: 30-day backup retention

### Recovery Procedures
- **RTO (Recovery Time Objective)**: < 15 minutes
- **RPO (Recovery Point Objective)**: < 5 minutes data loss
- **Automated Recovery**: Self-healing services
- **Manual Recovery**: Documented procedures
- **Testing**: Regular disaster recovery drills

## Deployment Architecture

### Development Environment
- **Local Development**: Docker Compose setup
- **Database**: SQLite for simplicity
- **Cache**: Redis single instance
- **AI**: Local Ollama deployment
- **Hot Reload**: Live code reloading

### Staging Environment
- **Container Orchestration**: Docker Swarm/Kubernetes
- **Database**: PostgreSQL with replication
- **Cache**: Redis Cluster
- **Load Balancer**: Nginx
- **Monitoring**: Basic monitoring stack

### Production Environment
- **Container Platform**: Kubernetes cluster
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis Cluster with failover
- **Load Balancer**: HAProxy with SSL termination
- **CDN**: CloudFlare for static assets
- **Monitoring**: Full observability stack
- **Security**: WAF, DDoS protection, SSL certificates

### CI/CD Pipeline
- **Source Control**: Git with feature branches
- **Automated Testing**: Unit, integration, contract tests
- **Code Quality**: ESLint, Pylint, SonarQube
- **Security Scanning**: Vulnerability assessments
- **Deployment**: Blue-green deployments
- **Rollback**: Automated rollback on failure

## Technology Stack Summary

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Cache**: Redis
- **ORM**: SQLAlchemy
- **Authentication**: JWT with PyJWT
- **WebSocket**: Python WebSockets
- **Task Queue**: Celery (optional)
- **Testing**: Pytest

### Frontend
- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Charts**: Chart.js
- **State Management**: React Context/Redux
- **HTTP Client**: Axios
- **WebSocket**: Native WebSocket API
- **Testing**: Jest, React Testing Library

### AI/ML
- **Model**: Ollama Gemma3:4b-it-q4_K_M
- **Deployment**: Local Ollama server
- **Processing**: NumPy, Pandas
- **Machine Learning**: Scikit-learn
- **Deep Learning**: Optional PyTorch integration

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **Load Balancer**: Nginx/HAProxy
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Security**: Let's Encrypt SSL, Fail2ban

### Development Tools
- **Package Management**: Poetry (Python), npm (Node.js)
- **Code Quality**: Black, isort, ESLint, Prettier
- **Version Control**: Git with conventional commits
- **CI/CD**: GitHub Actions
- **Documentation**: MkDocs
- **API Documentation**: OpenAPI/Swagger

This architecture ensures NIRAJ can handle high-frequency trading, real-time data processing, and enterprise-level security while maintaining scalability and reliability for production trading environments.