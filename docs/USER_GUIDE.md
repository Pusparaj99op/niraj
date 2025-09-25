# NIRAJ User Guide

## Welcome to NIRAJ Trading System

NIRAJ is an advanced AI-powered algorithmic trading platform designed for Bank Nifty options trading. This comprehensive user guide will help you understand, configure, and effectively use the platform to enhance your trading performance.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Trading Strategies](#trading-strategies)
4. [AI-Powered Features](#ai-powered-features)
5. [Risk Management](#risk-management)
6. [Portfolio Management](#portfolio-management)
7. [Real-time Monitoring](#real-time-monitoring)
8. [API Usage Guide](#api-usage-guide)
9. [Broker Integration](#broker-integration)
10. [Performance Analytics](#performance-analytics)
11. [Settings and Configuration](#settings-and-configuration)
12. [Mobile Trading](#mobile-trading)
13. [Troubleshooting](#troubleshooting)
14. [Frequently Asked Questions](#frequently-asked-questions)
15. [Best Practices](#best-practices)

---

## Getting Started

### Creating Your Account

1. **Registration**
   - Visit the NIRAJ platform registration page
   - Provide your email, phone number, and trading experience details
   - Verify your email and phone number
   - Complete KYC documentation if required

2. **Initial Setup**
   - Set your trading preferences and risk tolerance
   - Configure your broker connections (Angel One, Dhan)
   - Set up your trading capital allocation
   - Review and accept terms of service

### First Login

```
URL: https://your-niraj-platform.com
Username: Your registered email
Password: Your secure password
```

1. **Dashboard Welcome**
   - Complete the platform tour
   - Review safety guidelines
   - Set up two-factor authentication (recommended)

2. **Broker Integration**
   - Connect your Angel One account
   - Configure Dhan integration
   - Test connection status
   - Verify trading permissions

### Quick Start Checklist

- [ ] Account verified and activated
- [ ] Broker accounts connected and tested
- [ ] Initial capital allocation set
- [ ] Risk parameters configured
- [ ] First strategy selected and activated
- [ ] Notification preferences set
- [ ] Mobile app installed (optional)

---

## Dashboard Overview

### Main Dashboard Layout

The NIRAJ dashboard provides a comprehensive view of your trading activities:

#### 1. Header Section
- **Account Balance**: Real-time portfolio value
- **P&L Today**: Daily profit/loss summary
- **Active Strategies**: Number of running strategies
- **AI Status**: AI system health indicator
- **Notifications**: Alerts and system messages

#### 2. Market Overview Panel
```
Current Market Status
├── Bank Nifty: 45,234 (+0.34%)
├── Volatility Index: 12.5%
├── Market Sentiment: Bullish (76%)
└── Trading Session: Open until 3:30 PM
```

#### 3. Strategy Performance Grid
Real-time performance metrics for all active strategies:

| Strategy | Status | P&L (%) | Trades | Win Rate | Risk |
|----------|--------|---------|--------|----------|------|
| Predator Bull | Active | +2.4% | 12 | 75% | Medium |
| Volatility Hunter | Paused | +1.8% | 8 | 62% | High |
| Market Neutral | Active | +0.9% | 15 | 80% | Low |

#### 4. AI Insights Panel
- **Pattern Recognition**: Current market patterns identified
- **Confidence Scores**: AI prediction confidence levels
- **Recommended Actions**: AI-suggested trading opportunities
- **Market Sentiment**: News and social sentiment analysis

#### 5. Position Monitor
Real-time view of all open positions:
```
Open Positions (3)
├── BANKNIFTY 46000 CE - QTY: 100 - P&L: +₹2,450
├── BANKNIFTY 45500 PE - QTY: 50 - P&L: -₹850
└── BANKNIFTY 46500 CE - QTY: 75 - P&L: +₹1,200
```

### Navigation Menu

#### Primary Navigation
- **Dashboard**: Main overview screen
- **Strategies**: Strategy management and configuration
- **Portfolio**: Position management and analysis
- **Analytics**: Performance reports and insights
- **AI Monitor**: AI system status and predictions
- **Settings**: Platform and trading configuration
- **Help**: Documentation and support

#### Quick Actions Toolbar
- **Emergency Stop**: Immediately halt all trading
- **Strategy Pause**: Pause all strategies temporarily
- **Refresh Data**: Force data synchronization
- **Screenshot**: Capture dashboard for records
- **Export Data**: Download trading data

---

## Trading Strategies

### Strategy Categories

NIRAJ offers 20+ pre-built trading strategies across four main categories:

#### 1. Predatory Strategies
Aggressive strategies targeting quick profits from market inefficiencies:

**Bull Market Predator**
- **Objective**: Capitalize on strong bullish momentum
- **Instruments**: Call options with high delta
- **Risk Level**: High
- **Typical Duration**: 15-60 minutes
- **Best Conditions**: Strong uptrend with volume support

```json
{
  "name": "Bull Market Predator",
  "category": "predatory",
  "risk_level": "high",
  "parameters": {
    "entry_signal": "momentum_breakout",
    "stop_loss": 0.15,
    "take_profit": 0.30,
    "position_size": 0.05,
    "max_positions": 3
  }
}
```

**Bear Market Vulture**
- **Objective**: Profit from market declines and panic selling
- **Instruments**: Put options during market stress
- **Risk Level**: High
- **Typical Duration**: 30-120 minutes
- **Best Conditions**: Market downtrend with high volatility

#### 2. Quantitative Strategies
Data-driven strategies based on mathematical models:

**Statistical Arbitrage**
- **Objective**: Exploit temporary price discrepancies
- **Approach**: Mean reversion and correlation analysis
- **Risk Level**: Medium
- **Win Rate**: Typically 70-80%
- **Best Conditions**: Sideways or low-volatility markets

**Options Greeks Optimizer**
- **Objective**: Balance portfolio Greeks for optimal risk-return
- **Focus**: Delta, Gamma, Theta, Vega optimization
- **Risk Level**: Low to Medium
- **Typical Duration**: Full trading day
- **Best Conditions**: Any market condition

#### 3. Psychological Strategies
Strategies based on market psychology and behavioral patterns:

**Sentiment Reversal**
- **Objective**: Trade against extreme market sentiment
- **Indicators**: Put-call ratio, VIX, news sentiment
- **Risk Level**: Medium
- **Typical Duration**: 1-4 hours
- **Best Conditions**: Extreme fear or greed levels

**News Impact Trader**
- **Objective**: Trade on news-driven market reactions
- **Data Sources**: Economic news, earnings, policy announcements
- **Risk Level**: High
- **Response Time**: Within seconds of news release
- **Best Conditions**: High-impact news events

#### 4. Mathematical Strategies
Advanced mathematical and statistical approaches:

**Black-Scholes Arbitrage**
- **Objective**: Exploit mispricing in options valuations
- **Method**: Compare market prices to theoretical values
- **Risk Level**: Low to Medium
- **Profit Margin**: Small but consistent
- **Best Conditions**: Liquid markets with tight spreads

**Fibonacci Retracement**
- **Objective**: Trade based on Fibonacci levels
- **Entry Points**: 38.2%, 50%, 61.8% retracement levels
- **Risk Level**: Medium
- **Success Rate**: 60-70%
- **Best Conditions**: Trending markets with clear swings

### Strategy Configuration

#### Setting Up a New Strategy

1. **Strategy Selection**
   ```
   Navigate to Strategies → Add New Strategy
   ├── Choose Category (Predatory/Quantitative/Psychological/Mathematical)
   ├── Select Specific Strategy
   ├── Review Strategy Description
   └── Check Historical Performance
   ```

2. **Parameter Configuration**
   ```json
   {
     "risk_parameters": {
       "max_loss_per_trade": 0.02,
       "daily_loss_limit": 0.05,
       "position_size": 0.03,
       "max_concurrent_positions": 5
     },
     "entry_conditions": {
       "min_volume": 1000,
       "volatility_threshold": 0.15,
       "trend_strength": 0.6,
       "time_filter": "09:30-15:00"
     },
     "exit_conditions": {
       "profit_target": 0.25,
       "stop_loss": 0.10,
       "time_exit": "15:15",
       "volatility_exit": 0.05
     }
   }
   ```

3. **Testing and Validation**
   - **Paper Trading**: Test strategy with virtual money
   - **Backtesting**: Run against historical data
   - **Forward Testing**: Small live positions
   - **Full Deployment**: Live trading with full capital

#### Strategy Monitoring

**Real-time Strategy Dashboard**
```
Strategy: Bull Market Predator
Status: Active ●
Performance Today: +₹12,450 (+3.2%)
Trades: 8 executed, 6 profitable
Current Positions: 2 open
Risk Utilization: 45% of allocated capital

Recent Activity:
├── 14:23 - Opened BANKNIFTY 46000 CE (100 qty)
├── 14:18 - Closed BANKNIFTY 45800 CE (+₹2,100)
├── 14:12 - Opened BANKNIFTY 45900 PE (75 qty)
└── 14:08 - Closed BANKNIFTY 46200 CE (+₹1,850)
```

**Performance Metrics**
- **Win Rate**: Percentage of profitable trades
- **Average Profit/Loss**: Mean P&L per trade
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return measure
- **Profit Factor**: Gross profit / Gross loss ratio

### Advanced Strategy Features

#### Dynamic Position Sizing
```python
# Example: Kelly Criterion Position Sizing
position_size = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
position_size = max(0.01, min(0.10, position_size))  # Between 1% and 10%
```

#### Multi-Timeframe Analysis
- **1-minute**: Scalping and micro-trends
- **5-minute**: Short-term momentum
- **15-minute**: Intraday trend confirmation
- **1-hour**: Major trend analysis
- **Daily**: Long-term market structure

#### Correlation-Based Portfolio
```
Portfolio Correlation Matrix
                Bull    Bear    Neutral  Volatility
Bull Predator   1.00    -0.65   0.12     0.34
Bear Vulture   -0.65     1.00   0.08     0.42
Market Neutral  0.12     0.08   1.00    -0.15
Vol Hunter      0.34     0.42  -0.15     1.00
```

---

## AI-Powered Features

### Ollama Gemma3 Integration

NIRAJ leverages advanced AI to enhance trading decisions:

#### Pattern Recognition
The AI system continuously analyzes market data to identify:

**Chart Patterns**
- Head and Shoulders
- Double Top/Bottom
- Triangle formations
- Flag and Pennant patterns
- Cup and Handle

**Example AI Analysis**
```
AI Pattern Detection: Head and Shoulders
Confidence: 87%
Timeframe: 15-minute chart
Expected Move: -2.5% to -3.8%
Probability: 76%
Recommended Action: Consider PUT options
Entry Level: Below 45,850
Target: 44,200-44,500
Stop Loss: Above 46,100
```

#### Market Sentiment Analysis
Real-time sentiment analysis from multiple sources:

**News Sentiment Pipeline**
```
1. News Collection
   ├── Economic Times
   ├── Business Standard
   ├── Reuters
   └── Bloomberg

2. AI Processing
   ├── Text Analysis
   ├── Sentiment Scoring
   ├── Impact Assessment
   └── Trend Identification

3. Trading Signals
   ├── Bullish News: +0.73 sentiment
   ├── Bearish News: -0.45 sentiment
   ├── Market Impact: High (0.82)
   └── Recommended Action: Reduce positions
```

**Social Media Sentiment**
- Twitter sentiment analysis
- Reddit discussions monitoring
- Financial influencer tracking
- Retail trader sentiment gauge

#### Predictive Analytics

**Price Movement Prediction**
```json
{
  "prediction_horizon": "1_hour",
  "current_price": 45234,
  "predicted_range": {
    "lower": 44890,
    "upper": 45580,
    "most_likely": 45156
  },
  "confidence": 0.78,
  "key_factors": [
    "Technical momentum",
    "Options flow",
    "Market sentiment",
    "Volume patterns"
  ]
}
```

**Volatility Forecasting**
```json
{
  "current_iv": 15.6,
  "predicted_iv": {
    "30_min": 16.2,
    "1_hour": 17.1,
    "2_hour": 15.8
  },
  "volatility_regime": "medium",
  "confidence": 0.84
}
```

### RAG System (Retrieval-Augmented Generation)

The RAG system provides context-aware trading insights:

#### Historical Pattern Matching
```
Query: "Similar to current market conditions"

Retrieved Patterns:
1. Date: 2024-01-15, Similarity: 94%
   Pattern: Morning gap-up with volume surge
   Outcome: +2.1% move, lasted 45 minutes

2. Date: 2024-02-03, Similarity: 89%
   Pattern: Breakout above resistance
   Outcome: +1.8% move, with pullback after 1 hour

3. Date: 2024-02-28, Similarity: 87%
   Pattern: High volatility expansion
   Outcome: Sideways movement, mean reversion
```

#### Strategy Recommendation Engine
```
Current Market: Bullish momentum, high volume
Recommended Strategies:
1. Bull Market Predator (Match: 92%)
2. Momentum Breakout (Match: 88%)
3. Volume Surge (Match: 85%)

Avoid Strategies:
1. Mean Reversion (Low probability)
2. Contrarian plays (Against trend)
3. Low volatility strategies
```

### Confidence Tracking System

#### AI Prediction Accuracy
```
Model Performance (Last 30 Days)
├── Direction Prediction: 78% accuracy
├── Volatility Forecast: 0.92 correlation
├── Pattern Recognition: 83% success rate
└── News Impact: 71% accuracy

Confidence Calibration:
├── High Confidence (>80%): 89% accuracy
├── Medium Confidence (60-80%): 74% accuracy
├── Low Confidence (<60%): 58% accuracy
└── Overall Calibration: Well-calibrated
```

#### Adaptive Learning
The system continuously learns from trading outcomes:

```python
# Learning feedback loop
def update_model_confidence(prediction_id, actual_outcome):
    """Update model confidence based on actual results"""
    accuracy = calculate_accuracy(prediction, actual_outcome)
    model.update_confidence_weights(accuracy)

    # Adjust future predictions
    if accuracy > 0.8:
        model.increase_confidence_factor(0.05)
    elif accuracy < 0.6:
        model.decrease_confidence_factor(0.03)
```

---

## Risk Management

### Comprehensive Risk Framework

NIRAJ implements multiple layers of risk management:

#### 1. Position-Level Risk
**Individual Trade Limits**
```json
{
  "max_position_size": "3% of capital",
  "stop_loss": "10-15% per trade",
  "take_profit": "20-30% per trade",
  "max_holding_time": "4 hours",
  "risk_reward_ratio": "minimum 1:1.5"
}
```

**Dynamic Stop Loss**
- **Time-based**: Exit by 3:15 PM IST
- **Volatility-based**: Adjust based on ATR
- **Technical-based**: Below support levels
- **P&L-based**: Fixed percentage loss

#### 2. Portfolio-Level Risk
**Diversification Rules**
```
Portfolio Allocation Limits:
├── Maximum 40% in any single strategy
├── Maximum 25% in high-risk strategies
├── Minimum 30% in low-risk strategies
├── Maximum 60% directional exposure
└── Maximum 5 concurrent positions
```

**Correlation Management**
```python
# Correlation-based position sizing
def calculate_position_size(strategy, existing_positions):
    base_size = 0.03  # 3% base allocation

    # Reduce size if highly correlated positions exist
    for position in existing_positions:
        correlation = get_strategy_correlation(strategy, position.strategy)
        if correlation > 0.7:
            base_size *= (1.0 - correlation * 0.5)

    return max(0.01, base_size)  # Minimum 1%
```

#### 3. System-Level Risk
**Daily Limits**
- **Maximum Daily Loss**: 5% of capital
- **Maximum Daily Trades**: 50 per strategy
- **Maximum Daily Turnover**: 20x capital
- **Cooling-off Period**: After 3 consecutive losses

**Emergency Controls**
```
Risk Alert Levels:
├── Level 1 (2% daily loss): Reduce position sizes by 50%
├── Level 2 (3.5% daily loss): Pause high-risk strategies
├── Level 3 (5% daily loss): Stop all trading immediately
└── Manual Override: Always available for immediate stop
```

### Risk Monitoring Dashboard

#### Real-time Risk Metrics
```
Current Risk Status: ● GREEN
├── Daily P&L: +₹8,450 (+1.2%)
├── Maximum Drawdown: -₹2,100 (-0.3%)
├── Risk Utilization: 45% of maximum
├── VaR (95%): ₹12,500
├── Expected Shortfall: ₹18,750
└── Correlation Risk: LOW

Position Risk Breakdown:
├── BANKNIFTY 46000 CE: ₹3,200 (0.8% risk)
├── BANKNIFTY 45500 PE: ₹2,800 (0.7% risk)
├── BANKNIFTY 46500 CE: ₹2,400 (0.6% risk)
└── Total Portfolio Risk: ₹8,400 (2.1% risk)
```

#### Risk Alerts and Notifications
```
Alert System Configuration:
├── SMS Alerts: High-risk situations
├── Email Alerts: Daily risk reports
├── Push Notifications: Position updates
├── Desktop Alerts: Emergency stops
└── WhatsApp: Major P&L changes
```

### Advanced Risk Features

#### Monte Carlo Simulation
```python
# Portfolio risk simulation
simulation_results = {
    "1_day_var_95": 12500,  # 95% confidence, 1-day VaR
    "1_week_var_95": 28000,  # 95% confidence, 1-week VaR
    "max_expected_loss": 45000,  # Worst-case scenario
    "probability_profit": 0.73,  # Probability of daily profit
    "expected_return": 2800  # Expected daily return
}
```

#### Stress Testing
```
Stress Test Scenarios:
├── Market Crash (-5% in 15 minutes)
│   └── Expected Loss: ₹23,500
├── Volatility Spike (+50% IV expansion)
│   └── Expected Impact: ₹8,200 loss
├── Gap Opening (±2% overnight gap)
│   └── Expected Impact: ±₹12,000
└── Interest Rate Change (RBI policy)
    └── Expected Impact: ₹5,500 loss
```

---

## Portfolio Management

### Portfolio Overview

#### Real-time Portfolio Dashboard
```
PORTFOLIO SUMMARY
Total Capital: ₹10,00,000
Available Balance: ₹6,45,000
Invested Amount: ₹3,55,000
Today's P&L: +₹12,450 (+1.24%)
All-time P&L: +₹89,250 (+8.93%)

ASSET ALLOCATION
├── Options Positions: 60% (₹6,00,000)
├── Cash/Margin: 35% (₹3,50,000)
├── Reserved Capital: 5% (₹50,000)
└── Emergency Fund: Available

STRATEGY ALLOCATION
├── Predatory Strategies: 35%
├── Quantitative Strategies: 30%
├── Psychological Strategies: 20%
├── Mathematical Strategies: 15%
└── Manual Positions: 0%
```

#### Holdings Analysis
```
CURRENT POSITIONS (8 Active)
┌──────────────────┬─────┬──────┬──────────┬────────┬──────┐
│ Instrument       │ Qty │ Avg  │ Current  │ P&L    │ %    │
├──────────────────┼─────┼──────┼──────────┼────────┼──────┤
│ BN 46000 CE      │ 100 │ 45.2 │ 67.8     │ +2,260 │ +50% │
│ BN 45500 PE      │ 75  │ 28.4 │ 31.2     │ +210   │ +10% │
│ BN 46500 CE      │ 50  │ 22.1 │ 18.9     │ -160   │ -14% │
│ BN 45000 PE      │ 125 │ 15.6 │ 8.2      │ -925   │ -47% │
└──────────────────┴─────┴──────┴──────────┴────────┴──────┘
```

### Portfolio Analytics

#### Performance Metrics
```
PERFORMANCE ANALYSIS (Last 30 Days)
├── Total Return: +8.24%
├── Annualized Return: +98.88%
├── Volatility: 24.56%
├── Sharpe Ratio: 4.02
├── Maximum Drawdown: -3.21%
├── Calmar Ratio: 30.84
├── Win Rate: 74.2%
├── Profit Factor: 2.34
├── Average Trade: +₹847
└── Best Trade: +₹5,250
```

#### Risk-Adjusted Returns
```python
# Calculate risk-adjusted metrics
def calculate_portfolio_metrics(returns, risk_free_rate=0.06):
    return {
        'sharpe_ratio': (returns.mean() - risk_free_rate) / returns.std(),
        'sortino_ratio': (returns.mean() - risk_free_rate) / returns[returns < 0].std(),
        'max_drawdown': (returns.cumsum().expanding().max() - returns.cumsum()).max(),
        'var_95': returns.quantile(0.05),
        'expected_shortfall': returns[returns <= returns.quantile(0.05)].mean()
    }
```

#### Sector and Strategy Exposure
```
STRATEGY PERFORMANCE COMPARISON
┌─────────────────────┬────────┬──────┬──────┬──────────┐
│ Strategy            │ Return │ Risk │ SR   │ Capacity │
├─────────────────────┼────────┼──────┼──────┼──────────┤
│ Bull Predator       │ +12.4% │ HIGH │ 3.2  │ 15% max  │
│ Volatility Hunter   │ +8.9%  │ HIGH │ 2.8  │ 20% max  │
│ Market Neutral      │ +4.2%  │ LOW  │ 4.1  │ 40% max  │
│ Mean Reversion      │ +6.7%  │ MED  │ 3.5  │ 25% max  │
│ News Trader         │ +15.1% │ HIGH │ 2.9  │ 10% max  │
└─────────────────────┴────────┴──────┴──────┴──────────┘
```

### Position Management

#### Order Management System
```json
{
  "order_types": [
    {
      "name": "Market Order",
      "description": "Execute immediately at current market price",
      "use_case": "Quick execution, high liquidity instruments"
    },
    {
      "name": "Limit Order",
      "description": "Execute only at specified price or better",
      "use_case": "Price control, illiquid instruments"
    },
    {
      "name": "Stop Loss Order",
      "description": "Market order triggered at stop price",
      "use_case": "Risk management, position protection"
    },
    {
      "name": "Bracket Order",
      "description": "Entry with pre-defined stop loss and target",
      "use_case": "Complete trade management"
    }
  ]
}
```

#### Position Sizing Algorithm
```python
def calculate_optimal_position_size(strategy, market_conditions, portfolio_state):
    """Calculate optimal position size using multiple factors"""

    # Base size from Kelly Criterion
    kelly_size = calculate_kelly_size(strategy.win_rate, strategy.avg_win, strategy.avg_loss)

    # Adjust for volatility
    volatility_adjustment = min(1.0, 0.20 / market_conditions.volatility)

    # Adjust for correlation
    correlation_adjustment = calculate_correlation_penalty(strategy, portfolio_state)

    # Adjust for recent performance
    performance_adjustment = calculate_performance_adjustment(strategy.recent_performance)

    # Final position size
    position_size = kelly_size * volatility_adjustment * correlation_adjustment * performance_adjustment

    # Apply limits
    return max(0.01, min(0.05, position_size))  # Between 1% and 5%
```

#### Rebalancing Engine
```
AUTOMATIC REBALANCING
├── Frequency: Every 4 hours during market hours
├── Trigger: 10% deviation from target allocation
├── Method: Gradual rebalancing over 2 hours
├── Cost Optimization: Minimize transaction costs
└── Tax Efficiency: FIFO for profitable positions

Rebalancing Actions Today:
├── 11:30 AM: Reduced Bull Predator from 18% to 15%
├── 01:15 PM: Increased Market Neutral from 28% to 30%
├── 02:45 PM: Closed underperforming positions
└── Next Check: 4:00 PM
```

---

## Real-time Monitoring

### Live Trading Dashboard

#### Market Data Feed
```
REAL-TIME MARKET DATA
└── Bank Nifty Futures
    ├── Price: 45,234.50 ▲ +67.25 (+0.15%)
    ├── Volume: 4,23,567 (135% of avg)
    ├── Open Interest: 8,45,123 ▲ +12,456
    ├── Bid/Ask: 45,233.75 / 45,235.25
    ├── High/Low: 45,456.75 / 44,987.25
    └── VWAP: 45,189.34

└── Options Chain (ATM ±500)
    ├── 44500 PE: IV 16.2%, Vol 2,345
    ├── 45000 PE: IV 15.8%, Vol 8,567
    ├── 45500 CE: IV 15.5%, Vol 12,234
    ├── 46000 CE: IV 16.1%, Vol 6,789
    └── 46500 CE: IV 17.3%, Vol 3,456
```

#### Position Tracking
```
LIVE POSITION MONITOR
┌────────────────────────────────────────────────────────┐
│ BANKNIFTY 46000 CE | QTY: 100 | ENTRY: 45.20          │
│ Current: 67.80 | P&L: +₹2,260 (+49.9%) | Time: 1:23   │
│ ════════════════════════════════════════════════════   │
│ Strategy: Bull Predator | Risk: 0.8% | Target: +25%   │
│ Stop Loss: 40.68 (-10%) | Take Profit: 56.50 (+25%)   │
│ AI Confidence: 82% | Pattern: Bullish Breakout        │
└────────────────────────────────────────────────────────┘
```

#### Order Book and Execution
```
ORDER EXECUTION LOG
├── 14:23:45 - BUY 100 BANKNIFTY 46000 CE @ 45.20 ✓
├── 14:23:47 - Order Executed: 100 lots @ avg 45.25
├── 14:25:12 - SL Order Placed: 100 lots @ 40.68
├── 14:25:15 - TP Order Placed: 100 lots @ 56.50
└── Status: Position Active, Orders Set

PENDING ORDERS
├── SL: SELL 100 BN 46000 CE @ 40.68 (Stop Loss)
├── TP: SELL 100 BN 46000 CE @ 56.50 (Take Profit)
└── No other pending orders
```

### Alert System

#### Multi-Channel Notifications
```json
{
  "notification_channels": {
    "desktop": {
      "enabled": true,
      "priority_levels": ["high", "critical"],
      "sound_alerts": true
    },
    "mobile_push": {
      "enabled": true,
      "priority_levels": ["medium", "high", "critical"],
      "quiet_hours": "22:00-07:00"
    },
    "sms": {
      "enabled": true,
      "priority_levels": ["critical"],
      "phone": "+91-98765-43210"
    },
    "email": {
      "enabled": true,
      "priority_levels": ["low", "medium", "high", "critical"],
      "email": "trader@example.com"
    },
    "webhook": {
      "enabled": true,
      "url": "https://your-webhook.com/alerts",
      "priority_levels": ["high", "critical"]
    }
  }
}
```

#### Alert Types and Triggers
```
ALERT CONFIGURATION
├── Position Alerts
│   ├── P&L Threshold: ±₹5,000 or ±20%
│   ├── Time Exit Warning: 15 minutes before close
│   ├── Stop Loss Hit: Immediate notification
│   └── Take Profit Hit: Immediate notification
│
├── Strategy Alerts
│   ├── Strategy Stopped: Technical issues
│   ├── Daily Loss Limit: 80% of maximum reached
│   ├── Unusual Performance: >3σ deviation
│   └── New Opportunity: High-confidence signals
│
├── System Alerts
│   ├── Connection Lost: Broker API issues
│   ├── Data Feed Issues: Market data problems
│   ├── AI System Error: ML model failures
│   └── Margin Calls: Insufficient funds
│
└── Market Alerts
    ├── Volatility Spike: >50% IV increase
    ├── Volume Surge: >200% of average
    ├── News Impact: High-impact events
    └── Circuit Breakers: Market halts
```

### Performance Monitoring

#### Real-time Metrics Dashboard
```
LIVE PERFORMANCE METRICS
┌─────────────────────────────────────────┐
│ Today's Performance                     │
├─────────────────────────────────────────┤
│ Realized P&L: +₹8,450 (+0.85%)        │
│ Unrealized P&L: +₹4,200 (+0.42%)      │
│ Total P&L: +₹12,650 (+1.27%)          │
│ Trades Executed: 23                    │
│ Win Rate: 17/23 (73.9%)               │
│ Largest Win: +₹2,260                   │
│ Largest Loss: -₹980                    │
│ Average Trade: +₹550                   │
│ Maximum Drawdown: -₹1,200 (-0.12%)    │
└─────────────────────────────────────────┘
```

#### Strategy Performance Tracking
```python
# Real-time strategy metrics
def calculate_live_metrics(strategy_name, trades_today):
    """Calculate real-time strategy performance"""

    metrics = {
        'total_pnl': sum(trade.pnl for trade in trades_today),
        'win_rate': len([t for t in trades_today if t.pnl > 0]) / len(trades_today),
        'avg_win': np.mean([t.pnl for t in trades_today if t.pnl > 0]),
        'avg_loss': np.mean([t.pnl for t in trades_today if t.pnl < 0]),
        'profit_factor': abs(sum(t.pnl for t in trades_today if t.pnl > 0) /
                            sum(t.pnl for t in trades_today if t.pnl < 0)),
        'max_consecutive_losses': calculate_max_consecutive_losses(trades_today),
        'current_drawdown': calculate_current_drawdown(trades_today)
    }

    return metrics
```

---

## API Usage Guide

### Authentication

#### Getting API Access
1. **Enable API Access**
   ```
   Settings → API Management → Enable API Access
   ├── Generate API Key
   ├── Set API Permissions
   ├── Configure Rate Limits
   └── Download Client Libraries
   ```

2. **Authentication Headers**
   ```http
   POST /api/v1/auth/login
   Content-Type: application/json

   {
     "username": "your_username",
     "password": "your_password"
   }

   Response:
   {
     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
     "token_type": "Bearer",
     "expires_in": 3600
   }
   ```

3. **API Request Headers**
   ```http
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
   Content-Type: application/json
   X-API-Key: your_api_key
   ```

### Common API Endpoints

#### Portfolio Management
```http
GET /api/v1/portfolio
Authorization: Bearer {token}

Response:
{
  "total_value": 1000000,
  "available_balance": 645000,
  "invested_amount": 355000,
  "today_pnl": 12450,
  "total_pnl": 89250,
  "positions": [
    {
      "symbol": "BANKNIFTY46000CE",
      "quantity": 100,
      "avg_price": 45.20,
      "current_price": 67.80,
      "pnl": 2260,
      "pnl_percent": 49.9
    }
  ]
}
```

#### Strategy Management
```http
GET /api/v1/strategies
Authorization: Bearer {token}

Response:
{
  "strategies": [
    {
      "id": "bull_predator_1",
      "name": "Bull Market Predator",
      "status": "active",
      "pnl_today": 2450,
      "trades_today": 8,
      "win_rate": 0.75,
      "risk_level": "high"
    }
  ]
}
```

```http
POST /api/v1/strategies/{strategy_id}/start
Authorization: Bearer {token}
Content-Type: application/json

{
  "parameters": {
    "position_size": 0.03,
    "stop_loss": 0.10,
    "take_profit": 0.25
  }
}
```

#### Market Data
```http
GET /api/v1/market-data/banknifty
Authorization: Bearer {token}

Response:
{
  "symbol": "BANKNIFTY",
  "price": 45234.50,
  "change": 67.25,
  "change_percent": 0.15,
  "volume": 423567,
  "high": 45456.75,
  "low": 44987.25,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

#### Trading Operations
```http
POST /api/v1/orders
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "BANKNIFTY46000CE",
  "side": "buy",
  "quantity": 100,
  "order_type": "market",
  "strategy_id": "bull_predator_1"
}

Response:
{
  "order_id": "ORD-20240115-001",
  "status": "placed",
  "symbol": "BANKNIFTY46000CE",
  "quantity": 100,
  "side": "buy",
  "order_type": "market",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

### WebSocket Streaming

#### Real-time Data Feed
```javascript
// WebSocket connection for real-time data
const ws = new WebSocket('wss://api.niraj.com/ws');

ws.onopen = function() {
    // Subscribe to market data
    ws.send(JSON.stringify({
        "action": "subscribe",
        "stream": "market_data",
        "symbols": ["BANKNIFTY", "BANKNIFTY46000CE"]
    }));

    // Subscribe to portfolio updates
    ws.send(JSON.stringify({
        "action": "subscribe",
        "stream": "portfolio_updates"
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);

    switch(data.stream) {
        case 'market_data':
            updateMarketData(data);
            break;
        case 'portfolio_updates':
            updatePortfolio(data);
            break;
        case 'order_updates':
            updateOrders(data);
            break;
    }
};
```

#### Trading Signals Stream
```javascript
// Subscribe to AI trading signals
ws.send(JSON.stringify({
    "action": "subscribe",
    "stream": "ai_signals",
    "confidence_threshold": 0.75
}));

// Handle AI signals
function handleAISignal(signal) {
    console.log(`AI Signal: ${signal.action} ${signal.symbol}`);
    console.log(`Confidence: ${signal.confidence}`);
    console.log(`Reasoning: ${signal.reasoning}`);

    if (signal.confidence > 0.8 && autoTradingEnabled) {
        executeTradeBasedOnSignal(signal);
    }
}
```

### Python SDK

#### Installation and Setup
```bash
pip install niraj-trading-sdk
```

```python
from niraj_sdk import NIRAJClient

# Initialize client
client = NIRAJClient(
    api_key='your_api_key',
    api_secret='your_api_secret',
    base_url='https://api.niraj.com'
)

# Authenticate
client.login('username', 'password')
```

#### Basic Operations
```python
# Get portfolio
portfolio = client.get_portfolio()
print(f"Total P&L: ₹{portfolio.total_pnl}")

# Get strategies
strategies = client.get_strategies()
active_strategies = [s for s in strategies if s.status == 'active']

# Place order
order = client.place_order(
    symbol='BANKNIFTY46000CE',
    side='buy',
    quantity=100,
    order_type='market',
    strategy_id='bull_predator_1'
)

# Stream market data
@client.on_market_data
def handle_market_data(data):
    print(f"{data.symbol}: ₹{data.price} ({data.change_percent:+.2f}%)")

client.subscribe_market_data(['BANKNIFTY'])
```

---

## Broker Integration

### Supported Brokers

#### Angel One (Angel Broking)
**Configuration Steps:**
1. **Account Setup**
   ```
   NIRAJ Settings → Broker Connections → Angel One
   ├── Client ID: Your Angel One client ID
   ├── Password: Your trading password
   ├── API Key: Generated from Angel One portal
   ├── Secret Key: Generated from Angel One portal
   └── PIN: Your 4-digit PIN
   ```

2. **API Permissions**
   ```
   Required Permissions:
   ├── View Portfolio: ✓ Enabled
   ├── Place Orders: ✓ Enabled
   ├── Modify Orders: ✓ Enabled
   ├── Cancel Orders: ✓ Enabled
   ├── Historical Data: ✓ Enabled
   └── Real-time Feed: ✓ Enabled
   ```

3. **Connection Testing**
   ```python
   # Test Angel One connection
   angel_client = AngelOneClient(
       client_id="your_client_id",
       password="your_password",
       api_key="your_api_key",
       secret_key="your_secret_key",
       pin="your_pin"
   )

   # Test authentication
   login_result = angel_client.login()
   print(f"Login Status: {login_result.status}")

   # Test order placement
   test_order = angel_client.place_order(
       symbol="BANKNIFTY-EQ",
       side="BUY",
       quantity=1,
       order_type="MARKET"
   )
   ```

#### Dhan
**Configuration Steps:**
1. **Account Setup**
   ```
   NIRAJ Settings → Broker Connections → Dhan
   ├── Client ID: Your Dhan client ID
   ├── Access Token: Generated from Dhan portal
   ├── API Key: Your API key
   └── Trading Segment: F&O
   ```

2. **Risk Management Settings**
   ```json
   {
     "daily_loss_limit": 50000,
     "single_order_limit": 10000,
     "max_open_positions": 20,
     "allowed_products": ["MIS", "CNC", "NRML"],
     "allowed_exchanges": ["NSE", "BSE"]
   }
   ```

### Multi-Broker Management

#### Broker Selection Logic
```python
def select_optimal_broker(order_details):
    """Select best broker based on various factors"""

    factors = {
        'angel_one': {
            'latency': 50,  # milliseconds
            'success_rate': 0.98,
            'cost_per_trade': 15,
            'available_balance': get_angel_balance()
        },
        'dhan': {
            'latency': 45,
            'success_rate': 0.97,
            'cost_per_trade': 12,
            'available_balance': get_dhan_balance()
        }
    }

    # Score each broker
    scores = {}
    for broker, metrics in factors.items():
        score = (
            (100 - metrics['latency']) * 0.3 +  # Lower latency is better
            metrics['success_rate'] * 100 * 0.4 +  # Higher success rate is better
            (25 - metrics['cost_per_trade']) * 0.2 +  # Lower cost is better
            min(1.0, metrics['available_balance'] / order_details.value) * 10 * 0.1
        )
        scores[broker] = score

    return max(scores, key=scores.get)
```

#### Failover and Redundancy
```python
async def place_order_with_failover(order_details):
    """Place order with automatic failover"""

    primary_broker = select_optimal_broker(order_details)
    backup_brokers = [b for b in ['angel_one', 'dhan'] if b != primary_broker]

    # Try primary broker
    try:
        result = await brokers[primary_broker].place_order(order_details)
        if result.status == 'success':
            return result
    except Exception as e:
        logger.warning(f"Primary broker {primary_broker} failed: {e}")

    # Try backup brokers
    for backup_broker in backup_brokers:
        try:
            result = await brokers[backup_broker].place_order(order_details)
            if result.status == 'success':
                logger.info(f"Order placed successfully via backup broker: {backup_broker}")
                return result
        except Exception as e:
            logger.warning(f"Backup broker {backup_broker} failed: {e}")

    raise Exception("All brokers failed to place order")
```

### Order Management

#### Order Types Support
```
Supported Order Types by Broker:
┌─────────────────┬───────────┬──────┐
│ Order Type      │ Angel One │ Dhan │
├─────────────────┼───────────┼──────┤
│ Market          │ ✓         │ ✓    │
│ Limit           │ ✓         │ ✓    │
│ Stop Loss       │ ✓         │ ✓    │
│ Stop Loss Limit │ ✓         │ ✓    │
│ Bracket Order   │ ✓         │ ✓    │
│ Cover Order     │ ✓         │ ✗    │
│ Iceberg Order   │ ✗         │ ✓    │
│ After Market    │ ✓         │ ✓    │
└─────────────────┴───────────┴──────┘
```

#### Position Reconciliation
```python
async def reconcile_positions():
    """Reconcile positions across all brokers"""

    all_positions = {}
    discrepancies = []

    # Get positions from all brokers
    for broker_name, broker_client in brokers.items():
        try:
            positions = await broker_client.get_positions()
            all_positions[broker_name] = positions
        except Exception as e:
            logger.error(f"Failed to get positions from {broker_name}: {e}")

    # Compare with NIRAJ internal records
    internal_positions = await db.get_all_positions()

    for symbol in set().union(*[pos.keys() for pos in all_positions.values()]):
        broker_quantities = {
            broker: positions.get(symbol, {}).get('quantity', 0)
            for broker, positions in all_positions.items()
        }

        total_broker_quantity = sum(broker_quantities.values())
        internal_quantity = internal_positions.get(symbol, {}).get('quantity', 0)

        if total_broker_quantity != internal_quantity:
            discrepancies.append({
                'symbol': symbol,
                'internal_quantity': internal_quantity,
                'broker_quantities': broker_quantities,
                'difference': total_broker_quantity - internal_quantity
            })

    if discrepancies:
        await handle_position_discrepancies(discrepancies)

    return discrepancies
```

---

## Performance Analytics

### Comprehensive Performance Tracking

#### Daily Performance Report
```
DAILY PERFORMANCE REPORT - January 15, 2024
════════════════════════════════════════════

SUMMARY
├── Total P&L: +₹12,450 (+1.24%)
├── Realized P&L: +₹8,450
├── Unrealized P&L: +₹4,000
├── Trades Executed: 23 (17 wins, 6 losses)
├── Win Rate: 73.9%
├── Average Trade: +₹541
├── Best Trade: +₹2,260 (BANKNIFTY 46000 CE)
├── Worst Trade: -₹980 (BANKNIFTY 45000 PE)
├── Maximum Drawdown: -₹1,200 (-0.12%)
└── Sharpe Ratio: 4.2

STRATEGY BREAKDOWN
├── Bull Predator: +₹6,200 (8 trades, 75% win rate)
├── Volatility Hunter: +₹2,800 (5 trades, 80% win rate)
├── Market Neutral: +₹1,900 (7 trades, 71% win rate)
├── Mean Reversion: +₹1,550 (3 trades, 67% win rate)
└── Manual Trades: +₹0 (0 trades)

RISK METRICS
├── VaR (95%): ₹8,500
├── Expected Shortfall: ₹12,750
├── Beta to Nifty: 1.34
├── Correlation to Market: 0.78
└── Maximum Position Risk: 2.1%
```

#### Weekly Performance Analysis
```python
def generate_weekly_report(start_date, end_date):
    """Generate comprehensive weekly performance report"""

    trades = get_trades_in_period(start_date, end_date)

    # Calculate key metrics
    total_pnl = sum(trade.pnl for trade in trades)
    win_rate = len([t for t in trades if t.pnl > 0]) / len(trades)

    # Strategy performance
    strategy_performance = {}
    for trade in trades:
        if trade.strategy not in strategy_performance:
            strategy_performance[trade.strategy] = {
                'trades': 0, 'pnl': 0, 'wins': 0
            }

        strategy_performance[trade.strategy]['trades'] += 1
        strategy_performance[trade.strategy]['pnl'] += trade.pnl
        if trade.pnl > 0:
            strategy_performance[trade.strategy]['wins'] += 1

    # Risk analysis
    daily_returns = calculate_daily_returns(trades)
    max_drawdown = calculate_max_drawdown(daily_returns)
    sharpe_ratio = calculate_sharpe_ratio(daily_returns)

    return {
        'period': f"{start_date} to {end_date}",
        'total_pnl': total_pnl,
        'total_trades': len(trades),
        'win_rate': win_rate,
        'avg_trade': total_pnl / len(trades) if trades else 0,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'strategy_performance': strategy_performance,
        'best_day': max(daily_returns),
        'worst_day': min(daily_returns)
    }
```

### Advanced Analytics

#### Monte Carlo Analysis
```python
def run_monte_carlo_simulation(portfolio, num_simulations=10000, days=30):
    """Run Monte Carlo simulation for portfolio risk analysis"""

    # Historical returns and correlations
    returns_data = get_historical_returns(portfolio.assets, days=252)
    correlation_matrix = calculate_correlation_matrix(returns_data)

    # Generate random scenarios
    scenarios = []
    for _ in range(num_simulations):
        # Generate correlated random returns
        random_returns = generate_correlated_returns(
            correlation_matrix,
            days,
            portfolio.weights
        )

        # Calculate portfolio value path
        portfolio_values = simulate_portfolio_path(
            portfolio.initial_value,
            random_returns
        )

        scenarios.append({
            'final_value': portfolio_values[-1],
            'max_drawdown': calculate_max_drawdown(portfolio_values),
            'var_95': np.percentile(portfolio_values, 5),
            'returns': random_returns
        })

    # Analyze results
    results = {
        'probability_of_loss': len([s for s in scenarios if s['final_value'] < portfolio.initial_value]) / num_simulations,
        'expected_return': np.mean([s['final_value'] - portfolio.initial_value for s in scenarios]),
        'var_95': np.percentile([s['final_value'] for s in scenarios], 5),
        'expected_shortfall': np.mean([s['final_value'] for s in scenarios if s['final_value'] <= np.percentile([s['final_value'] for s in scenarios], 5)]),
        'max_drawdown_95': np.percentile([s['max_drawdown'] for s in scenarios], 95)
    }

    return results
```

#### Performance Attribution
```python
def analyze_performance_attribution(portfolio_returns, benchmark_returns, factors):
    """Analyze what factors contributed to portfolio performance"""

    # Factor loadings regression
    factor_loadings = calculate_factor_loadings(portfolio_returns, factors)

    # Attribution analysis
    attribution = {}

    # Market timing contribution
    timing_contribution = calculate_timing_contribution(
        portfolio_returns,
        benchmark_returns
    )

    # Security selection contribution
    selection_contribution = calculate_selection_contribution(
        portfolio_returns,
        benchmark_returns,
        portfolio.weights
    )

    # Factor contributions
    for factor_name, factor_returns in factors.items():
        factor_contribution = (
            factor_loadings[factor_name] *
            (factor_returns.mean() - benchmark_returns.mean())
        )
        attribution[f'{factor_name}_contribution'] = factor_contribution

    attribution.update({
        'timing_contribution': timing_contribution,
        'selection_contribution': selection_contribution,
        'total_active_return': portfolio_returns.mean() - benchmark_returns.mean(),
        'tracking_error': (portfolio_returns - benchmark_returns).std()
    })

    return attribution
```

### Custom Analytics Dashboard

#### Performance Visualization
```python
def create_performance_dashboard(trading_data):
    """Create comprehensive performance dashboard"""

    # Daily P&L chart
    daily_pnl = calculate_daily_pnl(trading_data)
    cumulative_pnl = daily_pnl.cumsum()

    # Strategy comparison
    strategy_returns = {}
    for strategy in get_unique_strategies(trading_data):
        strategy_trades = [t for t in trading_data if t.strategy == strategy]
        strategy_returns[strategy] = calculate_returns(strategy_trades)

    # Risk metrics over time
    rolling_sharpe = calculate_rolling_sharpe(daily_pnl, window=30)
    rolling_volatility = calculate_rolling_volatility(daily_pnl, window=30)
    rolling_max_dd = calculate_rolling_max_drawdown(cumulative_pnl, window=30)

    # Create dashboard
    dashboard = {
        'cumulative_pnl_chart': {
            'data': cumulative_pnl.to_dict(),
            'title': 'Cumulative P&L Over Time',
            'type': 'line_chart'
        },
        'strategy_comparison': {
            'data': strategy_returns,
            'title': 'Strategy Performance Comparison',
            'type': 'bar_chart'
        },
        'risk_metrics': {
            'sharpe_ratio': rolling_sharpe.to_dict(),
            'volatility': rolling_volatility.to_dict(),
            'max_drawdown': rolling_max_dd.to_dict(),
            'title': 'Risk Metrics Over Time',
            'type': 'multi_line_chart'
        },
        'summary_stats': {
            'total_return': cumulative_pnl.iloc[-1],
            'annualized_return': calculate_annualized_return(daily_pnl),
            'max_drawdown': rolling_max_dd.min(),
            'sharpe_ratio': rolling_sharpe.iloc[-1],
            'win_rate': calculate_win_rate(trading_data),
            'profit_factor': calculate_profit_factor(trading_data)
        }
    }

    return dashboard
```

This comprehensive user guide provides complete coverage of the NIRAJ trading system from a user perspective, including practical examples, configuration details, and best practices for successful algorithmic trading.
