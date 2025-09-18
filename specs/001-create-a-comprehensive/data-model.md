# Data Model: NIRAJ Trading System

**Date**: 17 September 2025  
**Feature**: NIRAJ Advanced Self-Learning Algorithmic AI Personal Trading System

## Core Entities

### 1. User
**Purpose**: Represents the trader/developer using the NIRAJ system  
**Storage**: SQLite table `users`

```python
@dataclass
class User:
    user_id: str                    # Primary key (UUID)
    username: str                   # Developer name
    created_at: datetime
    updated_at: datetime
    preferences: Dict[str, Any]     # JSON field for user settings
    
    # Authentication
    pin_hash: str                   # Hashed PIN for real trading mode
    last_login: datetime
    login_attempts: int            # Security tracking
    
    # Trading Settings
    default_capital: Decimal        # Default capital allocation
    risk_tolerance: float          # 0.0 to 1.0
    max_daily_loss: Decimal        # Maximum daily loss limit
    trading_mode: str              # "paper" or "live"
```

**Validation Rules**:
- PIN must be 4 digits (hashed using bcrypt)
- risk_tolerance between 0.0 and 1.0
- default_capital > 0
- trading_mode in ["paper", "live"]

**Relationships**:
- One-to-many with Portfolio
- One-to-many with Trade
- One-to-many with AuditLog

---

### 2. Security
**Purpose**: Represents tradable securities (Bank Nifty + constituent banks)  
**Storage**: SQLite table `securities`

```python
@dataclass
class Security:
    symbol: str                     # Primary key (e.g., "BANKNIFTY", "HDFCBANK")
    exchange: str                   # "NSE"
    instrument_type: str            # "INDEX", "EQUITY", "OPTION", "FUTURE"
    sector: str                     # "BANKING", "INDEX"
    lot_size: int                   # Standard lot size for F&O
    tick_size: Decimal              # Minimum price movement
    
    # Market Data
    last_price: Decimal
    last_updated: datetime
    market_cap: Decimal             # For individual banks
    
    # Status
    is_active: bool                # Currently tradable
    created_at: datetime
    updated_at: datetime
```

**Static Data**:
```python
BANK_NIFTY_CONSTITUENTS = [
    "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", 
    "INDUSINDBK", "IDFCFIRSTB", "FEDERALBNK", "AUBANK",
    "SBIN", "PNB", "BANKBARODA", "CANBK"
]
```

**Validation Rules**:
- symbol must be valid NSE symbol
- lot_size > 0
- tick_size > 0
- instrument_type in ["INDEX", "EQUITY", "OPTION", "FUTURE"]

**Relationships**:
- One-to-many with MarketData
- One-to-many with Trade
- One-to-many with Position

---

### 3. MarketData
**Purpose**: Stores historical and real-time market data  
**Storage**: SQLite table `market_data` (partitioned by symbol and date)

```python
@dataclass
class MarketData:
    id: str                         # Primary key (UUID)
    symbol: str                     # Foreign key to Security
    timestamp: datetime             # UTC+05:30 (IST)
    timeframe: str                  # "15min", "1day", "tick"
    
    # OHLCV Data
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    
    # Additional Fields
    change_percent: Decimal
    vwap: Decimal                   # Volume Weighted Average Price
    total_traded_value: Decimal
    
    # Data Quality
    data_source: str                # "angel_one", "dhan", "manual"
    is_validated: bool              # Data quality check passed
    created_at: datetime
```

**Indexing Strategy**:
- Primary index: (symbol, timestamp, timeframe)
- Secondary index: (timestamp) for time-based queries
- Partition by month for performance

**Validation Rules**:
- high_price >= max(open_price, close_price)
- low_price <= min(open_price, close_price)
- volume >= 0
- timeframe in ["tick", "15min", "1hour", "1day"]

**Relationships**:
- Many-to-one with Security
- Used by TechnicalIndicator calculations

---

### 4. TechnicalIndicator
**Purpose**: Pre-calculated technical analysis indicators  
**Storage**: SQLite table `technical_indicators`

```python
@dataclass
class TechnicalIndicator:
    id: str                         # Primary key (UUID)
    symbol: str                     # Foreign key to Security
    timestamp: datetime
    timeframe: str
    
    # Moving Averages
    sma_5: Optional[Decimal]        # Simple Moving Average
    sma_10: Optional[Decimal]
    sma_20: Optional[Decimal]
    sma_50: Optional[Decimal]
    ema_5: Optional[Decimal]        # Exponential Moving Average
    ema_10: Optional[Decimal]
    ema_20: Optional[Decimal]
    
    # Momentum Indicators
    rsi_14: Optional[Decimal]       # Relative Strength Index
    macd_signal: Optional[Decimal]  # MACD Signal Line
    macd_histogram: Optional[Decimal]
    stoch_k: Optional[Decimal]      # Stochastic %K
    stoch_d: Optional[Decimal]      # Stochastic %D
    
    # Volatility Indicators
    bb_upper: Optional[Decimal]     # Bollinger Band Upper
    bb_middle: Optional[Decimal]    # Bollinger Band Middle
    bb_lower: Optional[Decimal]     # Bollinger Band Lower
    atr_14: Optional[Decimal]       # Average True Range
    
    # Volume Indicators
    volume_sma_20: Optional[Decimal]
    on_balance_volume: Optional[Decimal]
    
    created_at: datetime
```

**Calculation Strategy**:
- Calculated in batch every 15 minutes
- Cached in Redis for real-time strategy access
- Fallback to database if Redis unavailable

**Validation Rules**:
- RSI between 0 and 100
- Stochastic %K and %D between 0 and 100
- ATR >= 0
- Volume indicators >= 0

---

### 5. Strategy
**Purpose**: Configuration and metadata for trading strategies  
**Storage**: SQLite table `strategies`

```python
@dataclass
class Strategy:
    strategy_id: str                # Primary key (UUID)
    name: str                       # Human-readable name
    category: str                   # "predatory", "quantitative", etc.
    description: str
    
    # Configuration
    parameters: Dict[str, Any]      # JSON field for strategy parameters
    target_symbols: List[str]       # Symbols this strategy trades
    min_confidence: float           # Minimum AI confidence to trade (0-1)
    max_position_size: Decimal      # Maximum position size per trade
    
    # Risk Parameters
    stop_loss_pct: Decimal          # Stop loss as percentage
    take_profit_pct: Decimal        # Take profit as percentage
    max_daily_trades: int           # Maximum trades per day
    
    # Status
    is_active: bool                 # Currently enabled
    is_paper_only: bool             # Restricted to paper trading
    created_at: datetime
    updated_at: datetime
    
    # Performance Tracking
    total_trades: int               # Lifetime trade count
    win_rate: float                 # Win percentage
    total_pnl: Decimal             # Lifetime P&L
    sharpe_ratio: float             # Risk-adjusted return
    max_drawdown: Decimal          # Maximum historical drawdown
```

**Strategy Categories**:
- "predatory": High-risk, high-reward strategies
- "quantitative": Mathematical and statistical strategies
- "psychological": Market psychology-based strategies
- "mathematical": Advanced mathematical models
- "extreme": Extreme risk strategies

**Validation Rules**:
- min_confidence between 0.0 and 1.0
- stop_loss_pct > 0, take_profit_pct > 0
- max_daily_trades > 0
- win_rate between 0.0 and 1.0

**Relationships**:
- One-to-many with StrategySignal
- One-to-many with Trade
- Many-to-many with Security (through target_symbols)

---

### 6. StrategySignal
**Purpose**: Trading signals generated by strategies  
**Storage**: SQLite table `strategy_signals`

```python
@dataclass
class StrategySignal:
    signal_id: str                  # Primary key (UUID)
    strategy_id: str                # Foreign key to Strategy
    symbol: str                     # Foreign key to Security
    timestamp: datetime             # Signal generation time
    
    # Signal Details
    signal_type: str                # "BUY", "SELL", "HOLD"
    confidence: float               # AI confidence score (0-1)
    strength: float                 # Signal strength (0-1)
    expected_duration: int          # Expected holding period (minutes)
    
    # Price Targets
    entry_price: Decimal            # Suggested entry price
    stop_loss: Decimal              # Stop loss price
    take_profit: Decimal            # Take profit price
    
    # Position Sizing
    suggested_quantity: int         # Recommended quantity
    risk_amount: Decimal            # Maximum risk for this trade
    
    # Execution Status
    status: str                     # "GENERATED", "EXECUTED", "IGNORED", "EXPIRED"
    executed_at: Optional[datetime]
    execution_price: Optional[Decimal]
    
    # AI Context
    ai_reasoning: str               # AI's reasoning for the signal
    market_context: Dict[str, Any]  # JSON field for market conditions
    
    created_at: datetime
```

**Status Flow**:
- GENERATED → EXECUTED (successful trade)
- GENERATED → IGNORED (filtered by risk management)
- GENERATED → EXPIRED (not executed within time limit)

**Validation Rules**:
- confidence between 0.0 and 1.0
- strength between 0.0 and 1.0
- signal_type in ["BUY", "SELL", "HOLD"]
- status in ["GENERATED", "EXECUTED", "IGNORED", "EXPIRED"]
- stop_loss != entry_price, take_profit != entry_price

**Relationships**:
- Many-to-one with Strategy
- Many-to-one with Security
- One-to-one with Trade (if executed)

---

### 7. Trade
**Purpose**: Executed trading transactions  
**Storage**: SQLite table `trades`

```python
@dataclass
class Trade:
    trade_id: str                   # Primary key (UUID)
    user_id: str                    # Foreign key to User
    strategy_id: str                # Foreign key to Strategy
    signal_id: Optional[str]        # Foreign key to StrategySignal (if from signal)
    symbol: str                     # Foreign key to Security
    
    # Trade Details
    trade_type: str                 # "BUY", "SELL"
    quantity: int                   # Number of shares/contracts
    entry_price: Decimal            # Actual execution price
    entry_timestamp: datetime       # Execution timestamp
    
    # Exit Details (for closed trades)
    exit_price: Optional[Decimal]   # Exit execution price
    exit_timestamp: Optional[datetime]
    exit_reason: Optional[str]      # "STOP_LOSS", "TAKE_PROFIT", "MANUAL", "STRATEGY"
    
    # Financial Details
    gross_pnl: Optional[Decimal]    # P&L before costs
    transaction_cost: Decimal       # Brokerage + taxes
    net_pnl: Optional[Decimal]      # P&L after costs
    
    # Risk Management
    initial_stop_loss: Decimal      # Initial stop loss
    current_stop_loss: Optional[Decimal]  # Current stop loss (may be trailed)
    take_profit_target: Decimal     # Take profit target
    
    # Trading Mode
    is_paper_trade: bool            # Paper vs live trade
    broker: str                     # "angel_one", "dhan", "paper"
    broker_order_id: Optional[str]  # Broker's order reference
    
    # Status
    status: str                     # "OPEN", "CLOSED", "CANCELLED"
    created_at: datetime
    updated_at: datetime
```

**Status Transitions**:
- OPEN → CLOSED (normal exit)
- OPEN → CANCELLED (order cancelled before fill)

**Validation Rules**:
- quantity > 0
- entry_price > 0
- For CLOSED trades: exit_price and exit_timestamp required
- net_pnl = gross_pnl - transaction_cost (when available)
- status in ["OPEN", "CLOSED", "CANCELLED"]

**Relationships**:
- Many-to-one with User
- Many-to-one with Strategy
- Many-to-one with Security
- One-to-one with StrategySignal (optional)

---

### 8. Portfolio
**Purpose**: Current positions and capital allocation  
**Storage**: SQLite table `portfolio`

```python
@dataclass
class Portfolio:
    portfolio_id: str               # Primary key (UUID)
    user_id: str                    # Foreign key to User
    symbol: str                     # Foreign key to Security
    
    # Position Details
    quantity: int                   # Current position size (+ for long, - for short)
    average_price: Decimal          # Average entry price
    current_price: Decimal          # Last market price
    market_value: Decimal           # Current market value
    
    # P&L Tracking
    unrealized_pnl: Decimal         # Current unrealized P&L
    realized_pnl: Decimal           # Realized P&L from closed trades
    total_pnl: Decimal              # Total P&L (realized + unrealized)
    
    # Risk Metrics
    position_risk: Decimal          # Value at risk for this position
    margin_used: Decimal            # Margin/capital allocated
    
    # Timestamps
    first_entry: datetime           # First trade timestamp
    last_updated: datetime          # Last position update
    
    # Metadata
    associated_strategies: List[str] # Strategies contributing to position
    is_paper_position: bool         # Paper vs live position
```

**Derived Calculations**:
- market_value = quantity × current_price
- unrealized_pnl = market_value - (quantity × average_price)
- total_pnl = realized_pnl + unrealized_pnl

**Validation Rules**:
- quantity != 0 (zero positions deleted)
- average_price > 0
- current_price > 0
- margin_used >= 0

**Relationships**:
- Many-to-one with User
- Many-to-one with Security
- Aggregated from Trade data

---

### 9. AIModel
**Purpose**: AI model state and performance tracking  
**Storage**: SQLite table `ai_models`

```python
@dataclass
class AIModel:
    model_id: str                   # Primary key (UUID)
    model_name: str                 # "gemma3_rag_v1"
    model_version: str              # Version string
    
    # Configuration
    model_path: str                 # Local Ollama model path
    rag_index_path: str            # Vector index path
    training_parameters: Dict[str, Any]  # JSON field
    
    # Performance Metrics
    total_predictions: int          # Total predictions made
    correct_predictions: int        # Correctly predicted outcomes
    accuracy: float                 # Prediction accuracy (0-1)
    confidence_calibration: Dict[str, float]  # Confidence vs actual accuracy
    
    # Learning State
    last_training_date: datetime
    training_data_size: int         # Number of training examples
    knowledge_cutoff: datetime      # Latest data used for training
    
    # Status
    is_active: bool                 # Currently in use
    created_at: datetime
    updated_at: datetime
```

**Performance Tracking**:
- Accuracy calculated as correct_predictions / total_predictions
- Confidence calibration tracks prediction confidence vs actual outcomes
- Regular retraining based on recent trading results

**Validation Rules**:
- accuracy between 0.0 and 1.0
- total_predictions >= 0
- correct_predictions <= total_predictions

**Relationships**:
- One-to-many with AIPrediction
- Used by Strategy for confidence scoring

---

### 10. AIPrediction
**Purpose**: Individual AI predictions and outcomes  
**Storage**: SQLite table `ai_predictions`

```python
@dataclass
class AIPrediction:
    prediction_id: str              # Primary key (UUID)
    model_id: str                   # Foreign key to AIModel
    strategy_id: str                # Foreign key to Strategy
    symbol: str                     # Foreign key to Security
    timestamp: datetime             # Prediction timestamp
    
    # Prediction Details
    predicted_direction: str        # "UP", "DOWN", "SIDEWAYS"
    confidence_score: float         # Model confidence (0-1)
    predicted_magnitude: Optional[float]  # Expected price change %
    prediction_horizon: int         # Prediction timeframe (minutes)
    
    # Context
    market_features: Dict[str, Any] # JSON field with input features
    reasoning: str                  # AI's reasoning text
    
    # Outcome Tracking
    actual_direction: Optional[str] # Actual price movement
    actual_magnitude: Optional[float]  # Actual price change %
    was_correct: Optional[bool]     # Prediction accuracy
    measured_at: Optional[datetime] # When outcome was measured
    
    # Performance Impact
    trade_executed: bool            # Whether prediction led to trade
    trade_pnl: Optional[Decimal]    # P&L if trade was executed
    
    created_at: datetime
```

**Outcome Measurement**:
- Predictions evaluated after prediction_horizon minutes
- Direction correctness: actual vs predicted direction
- Magnitude accuracy: within reasonable tolerance (±20%)

**Validation Rules**:
- confidence_score between 0.0 and 1.0
- predicted_direction in ["UP", "DOWN", "SIDEWAYS"]
- prediction_horizon > 0
- If measured: actual_direction in ["UP", "DOWN", "SIDEWAYS"]

**Relationships**:
- Many-to-one with AIModel
- Many-to-one with Strategy
- Many-to-one with Security

---

### 11. RiskMetric
**Purpose**: Risk management calculations and limits  
**Storage**: SQLite table `risk_metrics`

```python
@dataclass
class RiskMetric:
    metric_id: str                  # Primary key (UUID)
    user_id: str                    # Foreign key to User
    calculation_date: date          # Date of calculation
    
    # Portfolio Risk
    total_portfolio_value: Decimal
    total_margin_used: Decimal
    available_margin: Decimal
    portfolio_beta: float           # Portfolio beta vs Bank Nifty
    
    # Daily Risk Metrics
    daily_var: Decimal              # Value at Risk (95% confidence)
    max_daily_loss_limit: Decimal   # User-defined limit
    current_daily_pnl: Decimal      # Today's P&L
    daily_loss_used_pct: float      # % of daily loss limit used
    
    # Position Concentration
    max_single_position_pct: float  # Largest position as % of portfolio
    sector_concentration: Dict[str, float]  # JSON field
    strategy_concentration: Dict[str, float]  # JSON field
    
    # Drawdown Tracking
    peak_portfolio_value: Decimal   # Historical peak value
    current_drawdown: Decimal       # Current drawdown from peak
    max_drawdown: Decimal           # Maximum historical drawdown
    
    # Risk Violations
    active_violations: List[str]    # Current risk limit violations
    violation_count_today: int      # Number of violations today
    
    created_at: datetime
```

**Risk Calculations**:
- VaR calculated using historical simulation method
- Drawdown = (peak_value - current_value) / peak_value
- Concentration limits: single position <20%, single sector <50%

**Validation Rules**:
- total_portfolio_value >= 0
- available_margin >= 0
- daily_loss_used_pct between 0.0 and 1.0+
- current_drawdown >= 0

**Relationships**:
- Many-to-one with User
- Calculated from Portfolio and Trade data

---

### 12. AuditLog
**Purpose**: Comprehensive audit trail for compliance  
**Storage**: SQLite table `audit_logs` (high-volume, partitioned)

```python
@dataclass
class AuditLog:
    log_id: str                     # Primary key (UUID)
    timestamp: datetime             # UTC timestamp
    user_id: str                    # Foreign key to User
    
    # Event Details
    event_type: str                 # "TRADE", "LOGIN", "CONFIG_CHANGE", etc.
    event_category: str             # "TRADING", "SYSTEM", "SECURITY", "COMPLIANCE"
    description: str                # Human-readable description
    
    # Context
    entity_type: Optional[str]      # "Trade", "Strategy", etc.
    entity_id: Optional[str]        # ID of affected entity
    old_values: Optional[Dict[str, Any]]  # Previous values (for changes)
    new_values: Optional[Dict[str, Any]]  # New values (for changes)
    
    # System Context
    ip_address: Optional[str]       # Source IP address
    user_agent: Optional[str]       # Browser/client info
    session_id: Optional[str]       # Session identifier
    
    # Compliance
    requires_retention: bool        # Must be retained for regulatory period
    retention_until: date           # Retention end date (6 years for NSE)
    
    # Metadata
    severity: str                   # "INFO", "WARNING", "ERROR", "CRITICAL"
    source_module: str              # Module generating the log
```

**Event Types**:
- TRADE: Trade executions, modifications, cancellations
- STRATEGY: Strategy activation, parameter changes
- RISK: Risk violations, limit breaches
- AI: AI predictions, model updates
- AUTH: Login attempts, mode changes
- SYSTEM: System startup/shutdown, errors

**Retention Policy**:
- Trading events: 6 years (NSE requirement)
- System events: 1 year
- Security events: 3 years

**Validation Rules**:
- event_type not empty
- severity in ["INFO", "WARNING", "ERROR", "CRITICAL"]
- retention_until >= current_date

**Relationships**:
- Many-to-one with User
- References any entity via entity_type/entity_id

---

### 13. Configuration
**Purpose**: System and strategy configuration management  
**Storage**: SQLite table `configurations`

```python
@dataclass
class Configuration:
    config_id: str                  # Primary key (UUID)
    category: str                   # "TRADING", "API", "AI", "RISK"
    key: str                       # Configuration key
    value: str                     # Configuration value (JSON string)
    data_type: str                 # "string", "int", "float", "bool", "json"
    
    # Metadata
    description: str                # Human-readable description
    is_secret: bool                # Contains sensitive data
    is_user_configurable: bool     # User can modify
    requires_restart: bool         # System restart needed for changes
    
    # Validation
    validation_rules: Optional[str] # JSON schema for validation
    default_value: str             # Default value
    
    # Versioning
    version: int                   # Configuration version
    created_at: datetime
    updated_at: datetime
    updated_by: str                # User who made the change
```

**Configuration Categories**:
- TRADING: Capital limits, risk parameters, trading hours
- API: Broker credentials, API endpoints, rate limits  
- AI: Model parameters, confidence thresholds, training settings
- RISK: Position limits, stop-loss rules, circuit breakers

**Example Configurations**:
```python
{
    "TRADING.DEFAULT_CAPITAL": "100000.00",
    "TRADING.MAX_POSITION_SIZE_PCT": "10.0",
    "API.ANGEL_ONE.BASE_URL": "https://apiconnect.angelbroking.com",
    "AI.CONFIDENCE_THRESHOLD": "0.7",
    "RISK.MAX_DAILY_LOSS_PCT": "5.0"
}
```

**Validation Rules**:
- category in ["TRADING", "API", "AI", "RISK", "SYSTEM"]
- data_type in ["string", "int", "float", "bool", "json"]
- Secret values encrypted at rest

**Relationships**:
- Used by all other entities for configuration
- Versioned for change tracking

---

## Database Schema Relationships

```
User (1) ←→ (N) Portfolio
User (1) ←→ (N) Trade  
User (1) ←→ (N) RiskMetric
User (1) ←→ (N) AuditLog

Security (1) ←→ (N) MarketData
Security (1) ←→ (N) TechnicalIndicator
Security (1) ←→ (N) Trade
Security (1) ←→ (N) Portfolio

Strategy (1) ←→ (N) StrategySignal
Strategy (1) ←→ (N) Trade
Strategy (1) ←→ (N) AIPrediction

AIModel (1) ←→ (N) AIPrediction

StrategySignal (1) ←→ (1) Trade (optional)
```

## Data Validation & Integrity

### Constraints
- All monetary values use Decimal type for precision
- All timestamps in UTC+05:30 (IST)
- Foreign key constraints enforced
- Unique constraints on natural keys where applicable

### Data Quality Checks
- Market data validation (OHLC relationships)
- Price reasonableness checks (±10% daily moves flagged)
- Volume validation (non-negative, reasonable ranges)
- AI confidence scores between 0-1
- Risk metrics recalculated daily

### Backup Strategy
- Daily full backup to local storage
- Incremental backups every 4 hours during market hours
- Monthly backup to cloud storage (encrypted)
- Transaction log backup every hour

This data model provides a comprehensive foundation for the NIRAJ trading system, ensuring data integrity, audit compliance, and performance optimization.
