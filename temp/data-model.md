# Data Model: NIRAJ Algorithmic Trading System

**Date**: 17 September 2025  
**Context**: Entity definitions and relationships for trading system  
**Source**: Feature specification requirements and research findings

## Core Entities

### 1. Trade Entity
Represents individual trade executions with complete audit trail.

**Fields**:
- `id`: UUID, Primary Key
- `symbol`: String(20), Index symbol (BANKNIFTY, HDFCBANK, etc.)
- `quantity`: Integer, Number of shares/contracts
- `price`: Decimal(10,2), Execution price
- `order_type`: Enum(BUY, SELL), Trade direction
- `order_id`: String(50), Broker order reference
- `timestamp`: DateTime, Execution timestamp (UTC+05:30)
- `strategy_id`: UUID, Foreign Key to Strategy
- `status`: Enum(PENDING, EXECUTED, CANCELLED, REJECTED)
- `profit_loss`: Decimal(12,2), Realized P&L
- `commission`: Decimal(8,2), Brokerage charges
- `taxes`: Decimal(8,2), Applicable taxes
- `metadata`: JSON, Additional broker-specific data

**Validation Rules**:
- Price must be > 0
- Quantity must be > 0
- Symbol must exist in supported instruments
- Timestamp must be within market hours (9:15 AM - 3:30 PM IST)

**Relationships**:
- Many-to-One with Strategy
- Many-to-One with Portfolio

### 2. Strategy Entity
Defines trading strategies with configuration and performance metrics.

**Fields**:
- `id`: UUID, Primary Key
- `name`: String(100), Strategy name
- `description`: Text, Strategy description
- `category`: Enum(PREDATORY, QUANTITATIVE, PSYCHOLOGICAL, MATHEMATICAL, EXTREME)
- `risk_level`: Enum(LOW, MEDIUM, HIGH, EXTREME)
- `profit_potential`: String(50), Expected profit range
- `confidence_score`: Decimal(3,2), AI confidence (0.00-1.00)
- `is_active`: Boolean, Strategy activation status
- `parameters`: JSON, Strategy-specific parameters
- `performance_metrics`: JSON, Historical performance data
- `last_executed`: DateTime, Last execution timestamp
- `created_at`: DateTime, Creation timestamp
- `updated_at`: DateTime, Last update timestamp

**Validation Rules**:
- Confidence score must be between 0.00 and 1.00
- Parameters must match strategy schema
- Name must be unique

**Relationships**:
- One-to-Many with Trade
- Many-to-One with AIModel

### 3. MarketData Entity
Contains historical and real-time market data with OHLCV format.

**Fields**:
- `id`: UUID, Primary Key
- `symbol`: String(20), Trading symbol
- `timestamp`: DateTime, Data timestamp (UTC+05:30)
- `timeframe`: Enum(15MIN, 1DAY), Data granularity
- `open`: Decimal(10,2), Opening price
- `high`: Decimal(10,2), Highest price
- `low`: Decimal(10,2), Lowest price
- `close`: Decimal(10,2), Closing price
- `volume`: BigInteger, Trading volume
- `change_percent`: Decimal(5,2), Price change percentage
- `source`: Enum(ANGEL_ONE, DHAN, NSE_FEED), Data source
- `quality_score`: Integer, Data quality indicator (1-100)

**Validation Rules**:
- High >= max(Open, Close)
- Low <= min(Open, Close)
- Volume >= 0
- Change percent between -100.00 and 100.00
- Timestamp must be valid market time

**Relationships**:
- Many-to-One with Symbol (future extension)

### 4. Portfolio Entity
Manages user's trading positions and capital allocation.

**Fields**:
- `id`: UUID, Primary Key
- `user_id`: UUID, User identifier
- `total_capital`: Decimal(15,2), Total available capital
- `available_balance`: Decimal(15,2), Liquid cash balance
- `margin_used`: Decimal(15,2), Margin utilized
- `unrealized_pnl`: Decimal(12,2), Unrealized profit/loss
- `realized_pnl`: Decimal(12,2), Realized profit/loss
- `total_pnl`: Decimal(12,2), Total P&L
- `risk_metrics`: JSON, Risk assessment data
- `last_updated`: DateTime, Last update timestamp

**Validation Rules**:
- Available balance >= 0
- Total capital = available_balance + margin_used + unrealized_pnl
- Risk metrics must include VaR, max drawdown, Sharpe ratio

**Relationships**:
- One-to-Many with Position
- One-to-Many with Trade

### 5. Position Entity
Tracks individual security positions in the portfolio.

**Fields**:
- `id`: UUID, Primary Key
- `portfolio_id`: UUID, Foreign Key to Portfolio
- `symbol`: String(20), Security symbol
- `quantity`: Integer, Current position size
- `average_price`: Decimal(10,2), Average acquisition price
- `current_price`: Decimal(10,2), Latest market price
- `unrealized_pnl`: Decimal(12,2), Unrealized P&L
- `market_value`: Decimal(12,2), Current market value
- `entry_timestamp`: DateTime, Position entry time
- `last_updated`: DateTime, Last update timestamp

**Validation Rules**:
- Quantity can be negative (short positions)
- Average price > 0
- Market value = quantity * current_price

**Relationships**:
- Many-to-One with Portfolio
- Many-to-One with MarketData

### 6. User Entity
Developer/trader profile with authentication and preferences.

**Fields**:
- `id`: UUID, Primary Key
- `username`: String(50), Unique username
- `email`: String(100), Contact email
- `pin_hash`: String(128), Hashed PIN for real trading
- `api_key_angel`: String(128), Encrypted Angel One API key
- `api_secret_angel`: String(128), Encrypted Angel One API secret
- `api_key_dhan`: String(128), Encrypted Dhan API key
- `api_secret_dhan`: String(128), Encrypted Dhan API secret
- `trading_mode`: Enum(PAPER, REAL), Current trading mode
- `preferences`: JSON, User preferences and settings
- `created_at`: DateTime, Account creation timestamp
- `last_login`: DateTime, Last login timestamp

**Validation Rules**:
- Username must be unique
- Email must be valid format
- PIN hash must be present for real trading mode
- API credentials must be encrypted

### 7. AuditLog Entity
Records all system activities for compliance and analysis.

**Fields**:
- `id`: UUID, Primary Key
- `timestamp`: DateTime, Event timestamp
- `user_id`: UUID, User who triggered the event
- `action`: String(100), Action performed
- `resource`: String(100), Resource affected
- `resource_id`: UUID, Specific resource identifier
- `details`: JSON, Action details and parameters
- `ip_address`: String(45), Client IP address
- `user_agent`: String(200), Client user agent
- `status`: Enum(SUCCESS, FAILURE, WARNING), Action outcome

**Validation Rules**:
- Timestamp must be current or past
- Action must be from predefined list
- Details must be valid JSON

**Relationships**:
- Many-to-One with User

### 8. AIModel Entity
Ollama Gemma3 instance with training data and performance metrics.

**Fields**:
- `id`: UUID, Primary Key
- `model_name`: String(50), Ollama model identifier
- `version`: String(20), Model version
- `status`: Enum(LOADING, READY, ERROR), Model status
- `last_used`: DateTime, Last usage timestamp
- `performance_metrics`: JSON, Model performance data
- `training_data_stats`: JSON, Training data statistics
- `confidence_threshold`: Decimal(3,2), Minimum confidence for actions
- `learning_rate`: Decimal(5,4), Current learning rate

**Validation Rules**:
- Model name must match available Ollama models
- Confidence threshold between 0.00 and 1.00
- Performance metrics must include accuracy, latency, error rate

### 9. NewsFeed Entity
Aggregates news articles and social media sentiment.

**Fields**:
- `id`: UUID, Primary Key
- `title`: String(200), News title
- `content`: Text, Full article content
- `source`: String(50), News source (Reuters, Bloomberg, etc.)
- `url`: String(500), Original article URL
- `published_at`: DateTime, Publication timestamp
- `sentiment_score`: Decimal(3,2), Sentiment analysis (-1.00 to 1.00)
- `relevance_score`: Decimal(3,2), Trading relevance (0.00 to 1.00)
- `symbols`: JSON, Related trading symbols
- `categories`: JSON, News categories
- `processed_at`: DateTime, AI processing timestamp

**Validation Rules**:
- Sentiment score between -1.00 and 1.00
- Relevance score between 0.00 and 1.00
- URL must be valid format
- Symbols must be valid trading instruments

## Entity Relationships Diagram

```
User (1) ──── (N) Portfolio
    │
    ├── (N) AuditLog
    └── (1) AIModel

Portfolio (1) ──── (N) Position
    │
    └── (N) Trade

Trade (N) ──── (1) Strategy
    │
    └── (N) MarketData

Strategy (N) ──── (1) AIModel

MarketData (1) ──── (N) NewsFeed
```

## Data Integrity Constraints

### Primary Keys
- All entities use UUID v4 for primary keys
- No natural keys to ensure consistency

### Foreign Keys
- All foreign key relationships enforced at database level
- Cascade delete disabled to prevent accidental data loss
- Foreign key constraints validated before insertion

### Unique Constraints
- User.username: Unique across system
- Strategy.name: Unique across system
- Trade.order_id: Unique per broker

### Check Constraints
- Numeric ranges validated at database level
- Enum values restricted to predefined sets
- JSON fields validated for schema compliance

## Indexing Strategy

### Performance Indexes
- MarketData: (symbol, timestamp, timeframe)
- Trade: (strategy_id, timestamp, status)
- Position: (portfolio_id, symbol)
- AuditLog: (timestamp, user_id, action)

### Composite Indexes
- MarketData: (symbol, timeframe, timestamp DESC)
- Trade: (status, timestamp, symbol)

## Data Retention Policy

### Historical Data
- MarketData: 2 years rolling retention
- Trade: Indefinite retention
- AuditLog: 7 years retention (regulatory requirement)

### Archival Strategy
- Data older than retention period moved to cold storage
- Compressed CSV format for long-term storage
- Metadata preserved for compliance

## Migration Strategy

### Version Control
- Database schema version tracked in metadata table
- Migration scripts versioned with application code
- Rollback procedures defined for each migration

### Data Migration
- Zero-downtime migrations for production
- Data validation after each migration step
- Backup verification before migration execution

## Performance Considerations

### Query Optimization
- Use database indexes for frequent queries
- Implement query result caching with Redis
- Optimize JOIN operations with proper indexing

### Connection Pooling
- Connection pool size: 10-20 connections
- Connection timeout: 30 seconds
- Idle connection cleanup: 5 minutes

### Monitoring
- Query performance monitoring
- Connection pool utilization tracking
- Database health checks every 30 seconds