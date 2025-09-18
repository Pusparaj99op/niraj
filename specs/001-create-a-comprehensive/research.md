# Research: NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System

**Date**: 17 September 2025  
**Feature**: NIRAJ Trading System Implementation

## Research Summary

This research addresses the technical unknowns and best practices for implementing a comprehensive algorithmic trading system with AI integration, focusing on the Indian stock market (NSE) and Bank Nifty F&O trading.

## Technology Stack Decisions

### 1. Backend Framework
**Decision**: FastAPI with Python 3.11+  
**Rationale**: 
- Native async/await support for concurrent processing
- Automatic OpenAPI documentation generation
- High performance comparable to Node.js/Go
- Excellent WebSocket support for real-time data
- Strong typing with Pydantic for data validation
**Alternatives considered**: Django (too heavy), Flask (lacks async), Tornado (limited ecosystem)

### 2. AI/ML Integration
**Decision**: Ollama Gemma3:4b-it-q4_K_M with RAG (Retrieval-Augmented Generation)  
**Rationale**:
- Local deployment avoids API costs and latency
- Gemma3 optimized for reasoning and analysis tasks
- RAG enables continuous learning from market data
- 4b parameter model balances performance with resource usage
- q4_K_M quantization optimal for RTX 3050 GPU
**Alternatives considered**: OpenAI GPT-4 (expensive, latency), Llama2 (older, less capable), Claude (API dependency)

### 3. Real-time Data Processing
**Decision**: AsyncIO + WebSocket + Redis for caching  
**Rationale**:
- AsyncIO handles thousands of concurrent connections
- WebSocket provides sub-second market data updates
- Redis caches frequently accessed data (indicators, prices)
- Event-driven architecture for strategy triggers
**Alternatives considered**: Kafka (overkill for single instance), RabbitMQ (adds complexity), polling (too slow)

### 4. Database Strategy
**Decision**: SQLite for local data + CSV for historical data  
**Rationale**:
- SQLite sufficient for single-user trading system
- Zero configuration and maintenance overhead
- CSV format matches broker data exports
- Easy backup and data portability
- High performance for time-series queries with proper indexing
**Alternatives considered**: PostgreSQL (unnecessary complexity), InfluxDB (time-series but overkill), MongoDB (not suitable for financial data)

### 5. Frontend Technology
**Decision**: React.js with Vite bundler  
**Rationale**:
- Component-based architecture for trading widgets
- Large ecosystem for charting libraries (Chart.js, TradingView)
- Vite provides fast development and optimized builds
- WebSocket integration for real-time updates
- Dark theme support for trading environments
**Alternatives considered**: Vue.js (smaller ecosystem), Svelte (newer, less mature), vanilla JS (too much boilerplate)

## Trading-Specific Research

### 6. High-Frequency Trading (HFT) Requirements
**Decision**: Multi-threaded execution with order batching  
**Rationale**:
- Python GIL limitations overcome with ThreadPoolExecutor
- Order batching reduces API calls and improves latency
- Priority queues for time-sensitive strategies
- Direct broker API connections (no intermediaries)
**Best Practices**: 
- Use compiled extensions (Cython) for critical path calculations
- Pre-allocate memory for order objects
- Maintain persistent connections to broker APIs
- Implement circuit breakers for risk management

### 7. Strategy Architecture Pattern
**Decision**: Strategy Pattern with AI scoring integration  
**Rationale**:
- Each strategy as independent, testable class
- Common interface for signal generation and execution
- AI confidence scoring influences position sizing
- Easy to add/remove strategies without system changes
**Implementation Pattern**:
```python
class TradingStrategy(ABC):
    @abstractmethod
    async def analyze(self, market_data: dict) -> StrategySignal:
        pass
    
    async def get_ai_confidence(self, signal: StrategySignal) -> float:
        return await self.ai_model.score_signal(signal)
```

### 8. Risk Management Architecture
**Decision**: Multi-layered risk control with real-time monitoring  
**Rationale**:
- Position-level: Kelly Criterion for optimal sizing
- Strategy-level: Individual stop-loss and profit targets
- Portfolio-level: Maximum drawdown and correlation limits
- System-level: Circuit breakers and emergency stops
**Components**:
- Pre-trade risk checks (margin, concentration)
- Real-time P&L monitoring with alerts
- Regulatory compliance screening
- Audit trail for all risk decisions

### 9. Market Data Management
**Decision**: Hybrid approach with primary/fallback data sources  
**Rationale**:
- Angel One API as primary real-time source
- Dhan API as backup for redundancy
- Local CSV storage for historical backtesting
- Automatic gap detection and filling
**Data Validation**:
- Cross-reference prices between sources
- Detect and flag suspicious data points
- Maintain data quality metrics
- Automatic retry with exponential backoff

### 10. Authentication & Security
**Decision**: JWT tokens with automatic rotation + PIN protection  
**Rationale**:
- JWT tokens for API authentication (12-hour expiry)
- Automatic token refresh before expiration
- PIN (1937) protection for real trading mode
- Encrypted configuration storage for API keys
**Security Measures**:
- TLS 1.3 for all communications
- Rate limiting per API endpoint
- Request signing with HMAC-SHA256
- Audit logging for all authentication events

## Performance Optimizations

### 11. Latency Reduction Strategies
**Research Findings**:
- Use connection pooling for broker APIs
- Pre-compile trading strategies at startup
- Cache technical indicators with Redis
- Minimize memory allocation in hot paths
- Use uvloop for 10-15% performance improvement

### 12. Concurrent Processing Design
**Research Findings**:
- Separate threads for data ingestion, analysis, and execution
- Lock-free data structures where possible
- Producer-consumer pattern for order flow
- Dedicated thread pool for AI inference

## Regulatory Compliance Research

### 13. NSE Trading Regulations
**Key Requirements**:
- Order-to-trade ratio limits (varies by segment)
- Market manipulation detection and prevention
- Audit trail requirements (6 years retention)
- Risk management system mandatory
**Compliance Implementation**:
- Real-time monitoring of order patterns
- Automated screening against prohibited strategies
- Complete transaction logging with timestamps
- Regular compliance reporting generation

### 14. Tax Optimization Strategies
**Research Findings**:
- STCG (Short-term Capital Gains): 15% on F&O profits
- LTCG not applicable to F&O (all short-term)
- Business income vs capital gains classification
- Advance tax payments for regular profits
**Implementation**:
- Real-time P&L calculation with tax estimates
- Transaction categorization for reporting
- Integration with tax software APIs

## Testing Strategy Research

### 15. Strategy Backtesting Framework
**Decision**: Walk-forward analysis with out-of-sample testing  
**Rationale**:
- More realistic than simple backtesting
- Accounts for strategy degradation over time
- Prevents overfitting to historical data
- Includes transaction costs and slippage
**Metrics to Track**:
- Sharpe ratio, Sortino ratio, maximum drawdown
- Win rate, profit factor, average trade duration
- Risk-adjusted returns, volatility metrics

### 16. Paper Trading Implementation
**Decision**: Full simulation with realistic delays and costs  
**Rationale**:
- Test strategies without capital risk
- Validate AI learning mechanisms
- Stress-test system under various market conditions
- Train new strategies before live deployment
**Features**:
- Virtual capital management (₹1,00,000 default)
- Simulated broker latency and rejections
- Realistic transaction costs and slippage
- Performance comparison with live trading

## Development Workflow Optimization

### 17. Code Organization Best Practices
**Findings**:
- Use Poetry for dependency management (better than pip)
- Implement comprehensive logging with structured format
- Use type hints throughout codebase
- Automated code formatting with Black and isort
- Pre-commit hooks for code quality

### 18. Monitoring and Observability
**Decision**: Custom metrics with Prometheus + Grafana  
**Rationale**:
- Trading-specific metrics not available in standard tools
- Real-time alerting for system failures
- Performance tracking for strategy optimization
- Compliance reporting automation
**Key Metrics**:
- Order execution latency, API response times
- Strategy performance metrics, drawdown alerts
- System resource usage, error rates
- Market data quality and gaps

## Deployment and Infrastructure

### 19. Production Environment Setup
**Decision**: Local deployment with cloud backup  
**Rationale**:
- Minimizes latency to NSE servers (co-location advantages)
- Full control over system resources
- No cloud provider dependencies
- Cost-effective for single-user system
**Backup Strategy**:
- Daily automated backups to cloud storage
- Configuration versioning with Git
- Database replication for critical data
- Disaster recovery procedures documented

### 20. Monitoring and Alerting
**Decision**: Multi-channel alerting system  
**Rationale**:
- Email for non-urgent notifications
- SMS for critical trading alerts
- Desktop notifications for system status
- Telegram bot for mobile access
**Alert Categories**:
- Trading: Large losses, unusual patterns, API failures
- System: High CPU/memory, disk space, network issues
- Compliance: Regulatory violations, audit trail gaps

---

## Next Steps for Phase 1

Based on this research, Phase 1 should focus on:

1. **Data Model Design**: Define entities for trades, strategies, market data, and risk metrics
2. **API Contracts**: Design REST endpoints for strategy management, trading operations, and monitoring
3. **Database Schema**: Create tables for audit trails, performance metrics, and configuration
4. **AI Integration Contracts**: Define interfaces between strategies and AI confidence scoring
5. **WebSocket Protocol**: Design real-time data streaming format
6. **Configuration Management**: Structured YAML files for trading parameters and API keys

All unknowns from the Technical Context have been resolved with specific technology choices and implementation approaches justified by research findings.
