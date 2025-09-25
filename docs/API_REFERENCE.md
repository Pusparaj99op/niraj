# NIRAJ API Reference

## Overview

The NIRAJ API is a RESTful API with WebSocket support for real-time streaming. All API endpoints are versioned and use JSON for data exchange.

- **Base URL**: `http://localhost:8000/api/v1`
- **WebSocket URL**: `ws://localhost:8000/ws`
- **API Version**: v1
- **Content Type**: `application/json`
- **Authentication**: JWT Bearer Token

## Authentication

### Login
Authenticate and receive a JWT access token.

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string",
  "mfa_code": "string" // Optional, required if MFA enabled
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "string",
    "username": "string",
    "role": "string",
    "is_live_trading_enabled": false
  }
}
```

### Switch Trading Mode
Switch between paper trading and live trading modes.

```http
POST /api/v1/auth/switch-mode
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "mode": "live", // "paper" or "live"
  "pin": "1937"   // Required for live mode
}
```

**Response:**
```json
{
  "message": "Trading mode switched successfully",
  "current_mode": "live",
  "switched_at": "2024-01-01T12:00:00Z"
}
```

### Logout
Invalidate the current access token.

```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

## Strategies

### List Strategies
Get all available trading strategies.

```http
GET /api/v1/strategies
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `category` (optional): Filter by strategy category (predatory, quantitative, psychological, mathematical)
- `risk_level` (optional): Filter by risk level (low, medium, high, extreme)
- `active` (optional): Filter by active status (true/false)
- `limit` (optional): Number of results per page (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "strategies": [
    {
      "id": "string",
      "name": "The Predator Strategy",
      "description": "Order book analysis and institutional front-running",
      "category": "predatory",
      "risk_level": "high",
      "profit_potential": "500-1000%",
      "is_active": true,
      "confidence_score": 85.5,
      "parameters": {
        "position_size_percent": 0.1,
        "stop_loss_percent": 0.02,
        "take_profit_percent": 0.05
      },
      "performance_metrics": {
        "total_trades": 1247,
        "win_rate": 0.68,
        "avg_return": 0.034,
        "sharpe_ratio": 2.45,
        "max_drawdown": 0.12
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 20,
  "limit": 50,
  "offset": 0
}
```

### Create Strategy
Create a new custom trading strategy.

```http
POST /api/v1/strategies
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "My Custom Strategy",
  "description": "A custom algorithmic trading strategy",
  "category": "quantitative",
  "risk_level": "medium",
  "parameters": {
    "position_size_percent": 0.05,
    "stop_loss_percent": 0.015,
    "take_profit_percent": 0.03,
    "max_positions": 5,
    "indicators": ["RSI", "MACD", "BB"],
    "entry_conditions": {
      "rsi_oversold": 30,
      "macd_bullish_cross": true
    },
    "exit_conditions": {
      "rsi_overbought": 70,
      "stop_loss_hit": true,
      "take_profit_hit": true
    }
  },
  "is_active": false
}
```

**Response:**
```json
{
  "id": "string",
  "name": "My Custom Strategy",
  "message": "Strategy created successfully",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Get Strategy Details
Get detailed information about a specific strategy.

```http
GET /api/v1/strategies/{strategy_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "string",
  "name": "The Predator Strategy",
  "description": "Order book analysis and institutional front-running",
  "category": "predatory",
  "risk_level": "high",
  "profit_potential": "500-1000%",
  "is_active": true,
  "confidence_score": 85.5,
  "parameters": {
    "position_size_percent": 0.1,
    "stop_loss_percent": 0.02,
    "take_profit_percent": 0.05,
    "indicators": ["OrderBook", "VolumeProfile", "Momentum"],
    "entry_conditions": {
      "large_order_detected": true,
      "price_near_support": true,
      "volume_spike": 2.0
    }
  },
  "performance_metrics": {
    "total_trades": 1247,
    "winning_trades": 848,
    "losing_trades": 399,
    "win_rate": 0.68,
    "avg_winning_trade": 0.052,
    "avg_losing_trade": -0.019,
    "avg_return": 0.034,
    "total_return": 4.234,
    "sharpe_ratio": 2.45,
    "max_drawdown": 0.12,
    "profit_factor": 2.89,
    "recovery_factor": 35.28
  },
  "backtest_results": {
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 100000,
    "final_capital": 523400,
    "total_return": 423.4,
    "annualized_return": 423.4,
    "volatility": 0.189,
    "max_consecutive_losses": 5,
    "max_consecutive_wins": 12
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Update Strategy
Update an existing strategy's parameters.

```http
PUT /api/v1/strategies/{strategy_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Updated Strategy Name",
  "description": "Updated description",
  "parameters": {
    "position_size_percent": 0.08,
    "stop_loss_percent": 0.025
  },
  "is_active": true
}
```

**Response:**
```json
{
  "message": "Strategy updated successfully",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Delete Strategy
Delete a custom strategy (built-in strategies cannot be deleted).

```http
DELETE /api/v1/strategies/{strategy_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message": "Strategy deleted successfully"
}
```

### Backtest Strategy
Run a backtest on a specific strategy.

```http
POST /api/v1/strategies/{strategy_id}/backtest
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "initial_capital": 100000,
  "symbols": ["BANKNIFTY", "HDFCBANK"],
  "parameters": {
    "position_size_percent": 0.1,
    "stop_loss_percent": 0.02
  }
}
```

**Response:**
```json
{
  "backtest_id": "string",
  "status": "running", // running, completed, failed
  "progress": 0,
  "estimated_completion": "2024-01-01T12:05:00Z",
  "message": "Backtest started successfully"
}
```

## Trading

### List Trades
Get a list of all trades.

```http
GET /api/v1/trades
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `status` (optional): Filter by trade status (pending, executed, cancelled, expired)
- `strategy_id` (optional): Filter by strategy ID
- `symbol` (optional): Filter by trading symbol
- `start_date` (optional): Filter trades from this date (ISO 8601)
- `end_date` (optional): Filter trades until this date (ISO 8601)
- `limit` (optional): Number of results per page (default: 50)
- `offset` (optional): Offset for pagination (default: 0)

**Response:**
```json
{
  "trades": [
    {
      "id": "string",
      "strategy_id": "string",
      "strategy_name": "The Predator Strategy",
      "symbol": "BANKNIFTY24FEB50000CE",
      "side": "buy", // buy, sell
      "order_type": "market", // market, limit, stop, stop_limit
      "quantity": 100,
      "price": 45250.50,
      "executed_price": 45251.25,
      "executed_quantity": 100,
      "status": "executed",
      "pnl": 1250.75,
      "pnl_percent": 2.77,
      "commission": 15.50,
      "net_pnl": 1235.25,
      "entry_time": "2024-01-01T09:30:00Z",
      "exit_time": "2024-01-01T10:45:00Z",
      "holding_period": "01:15:00",
      "metadata": {
        "confidence_score": 87.5,
        "market_conditions": "trending",
        "volatility": 0.234
      }
    }
  ],
  "total": 1247,
  "limit": 50,
  "offset": 0,
  "summary": {
    "total_pnl": 42340.50,
    "total_trades": 1247,
    "winning_trades": 848,
    "losing_trades": 399,
    "win_rate": 0.68,
    "avg_holding_period": "02:34:12"
  }
}
```

### Execute Trade
Execute a new trade manually or through strategy.

```http
POST /api/v1/trades
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "strategy_id": "string", // Optional, for strategy-based trades
  "symbol": "BANKNIFTY24FEB50000CE",
  "side": "buy",
  "order_type": "limit",
  "quantity": 100,
  "price": 45250.00, // Required for limit orders
  "stop_loss": 44800.00, // Optional
  "take_profit": 46200.00, // Optional
  "time_in_force": "DAY", // DAY, GTC, IOC, FOK
  "metadata": {
    "reason": "manual_entry",
    "confidence": 85.0
  }
}
```

**Response:**
```json
{
  "trade_id": "string",
  "order_id": "string",
  "status": "pending",
  "message": "Trade order placed successfully",
  "created_at": "2024-01-01T09:30:00Z"
}
```

### Get Trade Details
Get detailed information about a specific trade.

```http
GET /api/v1/trades/{trade_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "string",
  "strategy_id": "string",
  "strategy_name": "The Predator Strategy",
  "symbol": "BANKNIFTY24FEB50000CE",
  "side": "buy",
  "order_type": "limit",
  "quantity": 100,
  "price": 45250.00,
  "executed_price": 45251.25,
  "executed_quantity": 100,
  "remaining_quantity": 0,
  "status": "executed",
  "pnl": 1250.75,
  "pnl_percent": 2.77,
  "commission": 15.50,
  "net_pnl": 1235.25,
  "entry_time": "2024-01-01T09:30:00Z",
  "exit_time": "2024-01-01T10:45:00Z",
  "holding_period": "01:15:00",
  "stop_loss": 44800.00,
  "take_profit": 46200.00,
  "time_in_force": "DAY",
  "fills": [
    {
      "price": 45251.25,
      "quantity": 100,
      "timestamp": "2024-01-01T09:30:15Z",
      "commission": 15.50
    }
  ],
  "metadata": {
    "confidence_score": 87.5,
    "market_conditions": "trending",
    "volatility": 0.234,
    "ai_signals": {
      "sentiment": 0.65,
      "technical_score": 0.82,
      "risk_score": 0.23
    }
  },
  "created_at": "2024-01-01T09:30:00Z",
  "updated_at": "2024-01-01T10:45:00Z"
}
```

### Update Trade
Update a pending trade or modify stop-loss/take-profit levels.

```http
PATCH /api/v1/trades/{trade_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "quantity": 150, // For pending trades
  "price": 45300.00, // For pending limit orders
  "stop_loss": 44900.00,
  "take_profit": 46500.00,
  "time_in_force": "GTC"
}
```

**Response:**
```json
{
  "message": "Trade updated successfully",
  "updated_at": "2024-01-01T10:30:00Z"
}
```

## Portfolio

### Get Portfolio Overview
Get overall portfolio information.

```http
GET /api/v1/portfolio
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "account_value": 523400.50,
  "initial_capital": 100000.00,
  "total_pnl": 423400.50,
  "total_pnl_percent": 423.4,
  "day_pnl": 2340.75,
  "day_pnl_percent": 0.45,
  "cash_balance": 85400.25,
  "invested_value": 438000.25,
  "margin_used": 125000.00,
  "margin_available": 398400.50,
  "buying_power": 1593602.00,
  "positions_count": 12,
  "open_orders_count": 3,
  "trading_mode": "paper", // paper, live
  "performance": {
    "total_return": 423.4,
    "annualized_return": 458.7,
    "sharpe_ratio": 2.45,
    "max_drawdown": 0.12,
    "win_rate": 0.68,
    "profit_factor": 2.89,
    "volatility": 0.189
  },
  "risk_metrics": {
    "portfolio_beta": 1.15,
    "value_at_risk_1d": 8450.30,
    "expected_shortfall": 12670.45,
    "concentration_risk": 0.23,
    "correlation_risk": 0.18
  },
  "updated_at": "2024-01-01T15:30:00Z"
}
```

### Get Positions
Get all current portfolio positions.

```http
GET /api/v1/portfolio/positions
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `strategy_id` (optional): Filter by strategy
- `status` (optional): Filter by position status (open, closed)

**Response:**
```json
{
  "positions": [
    {
      "symbol": "BANKNIFTY24FEB50000CE",
      "quantity": 100,
      "avg_price": 45251.25,
      "current_price": 46500.50,
      "market_value": 46500.50,
      "pnl": 1249.25,
      "pnl_percent": 2.76,
      "day_pnl": 340.75,
      "day_pnl_percent": 0.74,
      "cost_basis": 45251.25,
      "margin_used": 12500.00,
      "strategy_id": "string",
      "strategy_name": "The Predator Strategy",
      "entry_time": "2024-01-01T09:30:00Z",
      "holding_period": "06:00:00",
      "stop_loss": 44800.00,
      "take_profit": 46200.00,
      "risk_metrics": {
        "position_delta": 0.65,
        "position_gamma": 0.023,
        "position_theta": -45.30,
        "position_vega": 125.50
      }
    }
  ],
  "summary": {
    "total_positions": 12,
    "total_market_value": 438000.25,
    "total_pnl": 23400.75,
    "total_day_pnl": 1240.50,
    "margin_used": 125000.00
  }
}
```

### Get Performance Metrics
Get detailed portfolio performance analytics.

```http
GET /api/v1/portfolio/performance
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `period` (optional): Time period for analysis (1d, 1w, 1m, 3m, 6m, 1y, all)
- `benchmark` (optional): Benchmark for comparison (NIFTY50, BANKNIFTY)

**Response:**
```json
{
  "period": "1m",
  "start_date": "2023-12-01",
  "end_date": "2024-01-01",
  "performance": {
    "total_return": 23.45,
    "annualized_return": 281.4,
    "volatility": 0.189,
    "sharpe_ratio": 2.45,
    "sortino_ratio": 3.21,
    "calmar_ratio": 15.67,
    "max_drawdown": 0.12,
    "max_drawdown_duration": "3 days",
    "win_rate": 0.68,
    "profit_factor": 2.89,
    "recovery_factor": 35.28,
    "payoff_ratio": 2.74
  },
  "benchmark_comparison": {
    "benchmark": "BANKNIFTY",
    "benchmark_return": 8.45,
    "alpha": 15.00,
    "beta": 1.15,
    "correlation": 0.78,
    "tracking_error": 0.045,
    "information_ratio": 2.34
  },
  "monthly_returns": [
    {
      "month": "2023-12",
      "return": 23.45,
      "benchmark_return": 8.45,
      "trades": 89,
      "win_rate": 0.71
    }
  ],
  "risk_metrics": {
    "value_at_risk_1d": 8450.30,
    "value_at_risk_5d": 18920.45,
    "expected_shortfall": 12670.45,
    "conditional_var": 15230.80,
    "portfolio_beta": 1.15,
    "concentration_risk": 0.23,
    "correlation_risk": 0.18
  },
  "strategy_breakdown": [
    {
      "strategy_name": "The Predator Strategy",
      "contribution": 0.34,
      "return": 28.90,
      "trades": 34,
      "win_rate": 0.74
    }
  ]
}
```

## Market Data

### Get Market Data
Get current or historical market data for a symbol.

```http
GET /api/v1/market-data/{symbol}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `interval` (optional): Data interval (1m, 5m, 15m, 1h, 1d) - default: 15m
- `from` (optional): Start date (ISO 8601)
- `to` (optional): End date (ISO 8601)
- `limit` (optional): Number of data points (default: 100)

**Response:**
```json
{
  "symbol": "BANKNIFTY",
  "interval": "15m",
  "data": [
    {
      "timestamp": "2024-01-01T09:15:00Z",
      "open": 45200.50,
      "high": 45380.75,
      "low": 45180.25,
      "close": 45350.00,
      "volume": 1234567,
      "change": 149.50,
      "change_percent": 0.33,
      "vwap": 45285.30,
      "technical_indicators": {
        "rsi": 65.4,
        "sma_20": 45180.25,
        "ema_20": 45220.30,
        "bollinger_upper": 45450.80,
        "bollinger_lower": 44980.20,
        "macd": 45.30,
        "macd_signal": 38.50
      }
    }
  ],
  "current_price": 45350.00,
  "metadata": {
    "total_points": 96,
    "start_date": "2024-01-01T09:15:00Z",
    "end_date": "2024-01-01T15:30:00Z"
  }
}
```

## AI Predictions

### Get AI Predictions
Get current AI predictions and analysis.

```http
GET /api/v1/ai/predictions
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `symbol` (optional): Filter predictions for specific symbol
- `strategy` (optional): Filter predictions for specific strategy
- `confidence_min` (optional): Minimum confidence threshold (0-100)
- `timeframe` (optional): Prediction timeframe (short, medium, long)

**Response:**
```json
{
  "predictions": [
    {
      "id": "string",
      "symbol": "BANKNIFTY",
      "strategy": "The Predator Strategy",
      "prediction_type": "price_movement",
      "direction": "bullish", // bullish, bearish, neutral
      "confidence": 87.5,
      "timeframe": "short", // short (minutes), medium (hours), long (days)
      "predicted_price": 46200.00,
      "current_price": 45350.00,
      "price_change": 850.00,
      "price_change_percent": 1.87,
      "probability_up": 0.875,
      "probability_down": 0.125,
      "signals": {
        "technical": {
          "score": 0.82,
          "indicators": {
            "rsi_bullish": true,
            "macd_cross": true,
            "bollinger_squeeze": false,
            "volume_spike": true
          }
        },
        "sentiment": {
          "score": 0.65,
          "news_sentiment": 0.70,
          "social_sentiment": 0.60,
          "fear_greed_index": 68
        },
        "ai_analysis": {
          "pattern_recognition": 0.89,
          "market_regime": "trending",
          "volatility_forecast": 0.23,
          "support_levels": [45000, 44800, 44500],
          "resistance_levels": [45500, 45800, 46200]
        }
      },
      "risk_assessment": {
        "risk_score": 0.23,
        "max_loss_probability": 0.12,
        "expected_return": 0.0187,
        "risk_reward_ratio": 3.2,
        "value_at_risk": 1200.50
      },
      "metadata": {
        "model_version": "gemma3-v1.2",
        "training_data_points": 50000,
        "last_updated": "2024-01-01T15:25:00Z"
      },
      "created_at": "2024-01-01T15:30:00Z",
      "expires_at": "2024-01-01T16:30:00Z"
    }
  ],
  "summary": {
    "total_predictions": 15,
    "avg_confidence": 78.4,
    "bullish_predictions": 9,
    "bearish_predictions": 4,
    "neutral_predictions": 2
  },
  "model_status": {
    "status": "healthy",
    "last_training": "2024-01-01T06:00:00Z",
    "accuracy_24h": 0.847,
    "accuracy_7d": 0.823,
    "accuracy_30d": 0.798
  }
}
```

## System Status

### Get System Status
Get comprehensive system health and status information.

```http
GET /api/v1/system/status
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "status": "healthy", // healthy, degraded, unhealthy
  "version": "1.0.0",
  "environment": "production",
  "uptime": "72h 45m 30s",
  "timestamp": "2024-01-01T15:30:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time": 12,
      "connections": {
        "active": 8,
        "idle": 12,
        "max": 20
      },
      "storage": {
        "used": "2.4GB",
        "available": "97.6GB",
        "usage_percent": 2.4
      }
    },
    "cache": {
      "status": "healthy",
      "response_time": 3,
      "memory_usage": 45.6,
      "hit_rate": 0.94,
      "keys_count": 15420
    },
    "ai_engine": {
      "status": "healthy",
      "model": "gemma3:4b-it-q4_K_M",
      "response_time": 234,
      "gpu_usage": 67.5,
      "memory_usage": 4.2,
      "predictions_today": 1247
    },
    "websocket": {
      "status": "healthy",
      "active_connections": 23,
      "messages_per_second": 156,
      "avg_latency": 8
    },
    "brokers": {
      "angel_one": {
        "status": "connected",
        "last_heartbeat": "2024-01-01T15:29:45Z",
        "orders_today": 89,
        "api_rate_limit": {
          "remaining": 4850,
          "reset_time": "2024-01-01T16:00:00Z"
        }
      },
      "dhan": {
        "status": "connected",
        "last_heartbeat": "2024-01-01T15:29:50Z",
        "orders_today": 34,
        "api_rate_limit": {
          "remaining": 1950,
          "reset_time": "2024-01-01T16:00:00Z"
        }
      }
    }
  },
  "performance": {
    "cpu_usage": 23.5,
    "memory_usage": 67.8,
    "disk_usage": 15.4,
    "network_io": {
      "bytes_sent": 45230000,
      "bytes_received": 123450000
    },
    "api_metrics": {
      "requests_per_second": 45.2,
      "avg_response_time": 87,
      "error_rate": 0.002
    }
  },
  "alerts": [
    {
      "level": "warning",
      "message": "High memory usage detected",
      "component": "ai_engine",
      "timestamp": "2024-01-01T15:15:00Z"
    }
  ],
  "market_status": {
    "nse_status": "open", // open, closed, pre_open, post_close
    "market_hours": {
      "start": "09:15:00",
      "end": "15:30:00",
      "timezone": "Asia/Kolkata"
    },
    "next_trading_day": "2024-01-02",
    "holidays": [
      {
        "date": "2024-01-26",
        "name": "Republic Day"
      }
    ]
  }
}
```

## WebSocket API

### Connection
Connect to the WebSocket server for real-time data streams.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=your_jwt_token');

ws.onopen = function(event) {
    console.log('Connected to NIRAJ WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('WebSocket connection closed');
};
```

### Message Format
All WebSocket messages follow this format:

```json
{
  "type": "subscribe|unsubscribe|data|error|heartbeat",
  "stream": "market_data|trade_signals|portfolio|ai_insights",
  "data": {},
  "timestamp": "2024-01-01T15:30:00Z",
  "sequence": 12345
}
```

### Subscribe to Streams

#### Market Data Stream
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'market_data',
  symbols: ['BANKNIFTY', 'HDFCBANK', 'ICICIBANK']
}));
```

**Data Format:**
```json
{
  "type": "data",
  "stream": "market_data",
  "data": {
    "symbol": "BANKNIFTY",
    "price": 45350.00,
    "change": 149.50,
    "change_percent": 0.33,
    "volume": 1234567,
    "high": 45380.75,
    "low": 45180.25,
    "bid": 45349.75,
    "ask": 45350.25,
    "bid_size": 100,
    "ask_size": 150
  },
  "timestamp": "2024-01-01T15:30:15Z"
}
```

#### Trade Signals Stream
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'trade_signals'
}));
```

**Data Format:**
```json
{
  "type": "data",
  "stream": "trade_signals",
  "data": {
    "signal_id": "string",
    "strategy": "The Predator Strategy",
    "symbol": "BANKNIFTY24FEB50000CE",
    "action": "buy", // buy, sell, hold, close
    "confidence": 87.5,
    "price": 45350.00,
    "quantity": 100,
    "reason": "Large institutional order detected",
    "risk_score": 0.23,
    "expected_return": 0.0187,
    "stop_loss": 44800.00,
    "take_profit": 46200.00,
    "urgency": "high" // low, medium, high
  },
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### Portfolio Updates Stream
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'portfolio'
}));
```

**Data Format:**
```json
{
  "type": "data",
  "stream": "portfolio",
  "data": {
    "account_value": 523400.50,
    "day_pnl": 2340.75,
    "day_pnl_percent": 0.45,
    "positions": [
      {
        "symbol": "BANKNIFTY24FEB50000CE",
        "quantity": 100,
        "pnl": 1249.25,
        "pnl_percent": 2.76
      }
    ],
    "recent_trade": {
      "symbol": "HDFCBANK",
      "side": "buy",
      "quantity": 50,
      "price": 1650.25,
      "status": "executed"
    }
  },
  "timestamp": "2024-01-01T15:30:00Z"
}
```

#### AI Insights Stream
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  stream: 'ai_insights'
}));
```

**Data Format:**
```json
{
  "type": "data",
  "stream": "ai_insights",
  "data": {
    "insight_type": "market_analysis", // market_analysis, prediction, alert
    "title": "Market Momentum Shift Detected",
    "description": "AI detected a significant shift in market sentiment",
    "confidence": 89.2,
    "impact": "high", // low, medium, high
    "affected_symbols": ["BANKNIFTY", "HDFCBANK"],
    "recommendation": "Consider reducing position sizes in momentum strategies",
    "analysis": {
      "sentiment_change": -0.15,
      "volatility_forecast": 0.28,
      "probability_scenarios": {
        "bullish": 0.35,
        "bearish": 0.65
      }
    }
  },
  "timestamp": "2024-01-01T15:30:00Z"
}
```

### Unsubscribe from Streams
```javascript
ws.send(JSON.stringify({
  type: 'unsubscribe',
  stream: 'market_data'
}));
```

### Heartbeat
The WebSocket server sends periodic heartbeat messages:

```json
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T15:30:00Z",
  "server_time": "2024-01-01T15:30:00Z"
}
```

## Error Handling

### HTTP Error Responses
All API endpoints return structured error responses:

```json
{
  "error": "ValidationError",
  "message": "Invalid request parameters",
  "details": {
    "field": "quantity",
    "issue": "must be greater than 0"
  },
  "path": "/api/v1/trades",
  "timestamp": "2024-01-01T15:30:00Z",
  "request_id": "req_12345"
}
```

### Common Error Codes
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### WebSocket Error Messages
```json
{
  "type": "error",
  "error": "InvalidSubscription",
  "message": "Unknown stream type",
  "timestamp": "2024-01-01T15:30:00Z"
}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Authentication endpoints**: 10 requests per minute
- **Trading endpoints**: 100 requests per minute  
- **Market data endpoints**: 500 requests per minute
- **General endpoints**: 1000 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704110400
```

## Pagination

Endpoints that return lists support pagination:

**Request:**
```http
GET /api/v1/trades?limit=50&offset=100
```

**Response includes:**
```json
{
  "data": [...],
  "total": 1247,
  "limit": 50,
  "offset": 100,
  "has_next": true,
  "has_previous": true,
  "next_offset": 150,
  "previous_offset": 50
}
```

## API Versioning

The API uses URL versioning:
- Current version: `v1`
- Base URL: `/api/v1`
- Future versions will be available at `/api/v2`, etc.

Version compatibility is maintained for at least 12 months after a new version is released.