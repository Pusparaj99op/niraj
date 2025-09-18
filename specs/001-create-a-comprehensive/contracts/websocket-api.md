# WebSocket API Specification: NIRAJ Trading System

## Overview

The NIRAJ WebSocket API provides real-time data streaming for market data, trading signals, AI insights, system status, and portfolio updates. The WebSocket server runs on the same FastAPI backend (port 8000) with path `/ws`.

**Connection URL**: `ws://localhost:8000/ws`  
**Protocol**: WebSocket (RFC 6455)  
**Authentication**: JWT token passed as query parameter or in first message

## Connection Management

### Connection Establishment
```javascript
// Connect with JWT token
const ws = new WebSocket('ws://localhost:8000/ws?token=<JWT_TOKEN>');

// Or authenticate after connection
const ws = new WebSocket('ws://localhost:8000/ws');
ws.send(JSON.stringify({
    type: 'auth',
    token: '<JWT_TOKEN>'
}));
```

### Connection States
- **CONNECTING**: Initial connection attempt
- **AUTHENTICATED**: Successfully authenticated
- **SUBSCRIBED**: Active subscriptions established
- **DISCONNECTED**: Connection closed

### Heartbeat
- Client sends heartbeat every 30 seconds: `{"type": "ping"}`
- Server responds with: `{"type": "pong", "timestamp": "2025-09-17T10:30:00Z"}`
- Connection closed if no heartbeat received for 60 seconds

## Message Format

All messages use JSON format with a common structure:

```json
{
    "type": "message_type",
    "timestamp": "2025-09-17T10:30:00.000Z",
    "data": { /* message-specific payload */ },
    "correlation_id": "optional-uuid-for-request-response"
}
```

### Message Types

#### Client → Server (Outbound)
- `auth`: Authentication
- `subscribe`: Subscribe to data streams
- `unsubscribe`: Unsubscribe from data streams
- `ping`: Heartbeat
- `trade_request`: Execute trade
- `strategy_control`: Start/stop strategies

#### Server → Client (Inbound)
- `auth_response`: Authentication result
- `subscription_response`: Subscription confirmation
- `market_data`: Real-time market data
- `trade_signal`: Strategy trading signals
- `trade_execution`: Trade execution updates
- `ai_insight`: AI analysis and predictions
- `portfolio_update`: Portfolio/position changes
- `system_alert`: System status alerts
- `error`: Error messages
- `pong`: Heartbeat response

## Authentication

### Initial Authentication
```json
// Client → Server
{
    "type": "auth",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

// Server → Client (Success)
{
    "type": "auth_response",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "status": "authenticated",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "trading_mode": "paper",
        "session_id": "session_uuid"
    }
}

// Server → Client (Failure)
{
    "type": "auth_response",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "status": "failed",
        "error": "Invalid or expired token"
    }
}
```

## Subscriptions

### Subscribe to Data Streams
```json
// Client → Server
{
    "type": "subscribe",
    "data": {
        "streams": [
            {
                "stream_type": "market_data",
                "symbols": ["BANKNIFTY", "HDFCBANK"],
                "timeframe": "15min"
            },
            {
                "stream_type": "trade_signals",
                "strategy_ids": ["strategy_uuid_1", "strategy_uuid_2"]
            },
            {
                "stream_type": "ai_insights",
                "min_confidence": 0.7
            },
            {
                "stream_type": "portfolio_updates"
            },
            {
                "stream_type": "system_alerts",
                "severity": ["WARNING", "ERROR", "CRITICAL"]
            }
        ]
    }
}

// Server → Client
{
    "type": "subscription_response",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "status": "success",
        "active_subscriptions": [
            {
                "stream_type": "market_data",
                "symbols": ["BANKNIFTY", "HDFCBANK"],
                "subscription_id": "sub_uuid_1"
            },
            {
                "stream_type": "trade_signals",
                "subscription_id": "sub_uuid_2"
            }
        ],
        "failed_subscriptions": []
    }
}
```

### Unsubscribe from Data Streams
```json
// Client → Server
{
    "type": "unsubscribe",
    "data": {
        "subscription_ids": ["sub_uuid_1", "sub_uuid_2"]
    }
}
```

## Real-time Data Streams

### 1. Market Data Stream
Real-time OHLCV data and price updates

```json
{
    "type": "market_data",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "symbol": "BANKNIFTY",
        "timeframe": "15min",
        "ohlcv": {
            "timestamp": "2025-09-17T10:15:00Z",
            "open": 45150.25,
            "high": 45180.75,
            "low": 45125.00,
            "close": 45165.50,
            "volume": 125680,
            "change_percent": 0.85
        },
        "indicators": {
            "rsi_14": 65.4,
            "sma_20": 45120.30,
            "bb_upper": 45200.00,
            "bb_lower": 45050.00
        },
        "quote": {
            "bid": 45163.25,
            "ask": 45166.75,
            "last_price": 45165.50,
            "last_updated": "2025-09-17T10:30:15Z"
        }
    }
}
```

### 2. Trade Signals Stream
AI-generated trading signals from active strategies

```json
{
    "type": "trade_signal",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "signal_id": "signal_uuid",
        "strategy_id": "strategy_uuid",
        "strategy_name": "The Predator Strategy",
        "symbol": "HDFCBANK",
        "signal_type": "BUY",
        "confidence": 0.85,
        "strength": 0.92,
        "entry_price": 1650.25,
        "stop_loss": 1620.00,
        "take_profit": 1695.50,
        "suggested_quantity": 50,
        "risk_amount": 1512.50,
        "expected_duration": 180,
        "ai_reasoning": "Strong bullish momentum detected with RSI oversold bounce and volume spike. Bank sector showing relative strength.",
        "market_context": {
            "trend": "BULLISH",
            "volatility": "MODERATE",
            "volume_profile": "ABOVE_AVERAGE",
            "sector_sentiment": "POSITIVE"
        }
    }
}
```

### 3. Trade Execution Stream
Real-time trade execution updates

```json
{
    "type": "trade_execution",
    "timestamp": "2025-09-17T10:30:05Z",
    "data": {
        "trade_id": "trade_uuid",
        "event": "EXECUTED", // SUBMITTED, EXECUTED, PARTIAL_FILL, CANCELLED, REJECTED
        "symbol": "HDFCBANK",
        "trade_type": "BUY",
        "quantity": 50,
        "executed_quantity": 50,
        "execution_price": 1651.00,
        "strategy_id": "strategy_uuid",
        "broker": "angel_one",
        "broker_order_id": "AOB123456",
        "execution_time": "2025-09-17T10:30:05.123Z",
        "is_paper_trade": false,
        "transaction_cost": 45.75,
        "status": "OPEN"
    }
}
```

### 4. AI Insights Stream
Real-time AI analysis and predictions

```json
{
    "type": "ai_insight",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "insight_id": "insight_uuid",
        "insight_type": "MARKET_ANALYSIS", // PREDICTION, PATTERN_RECOGNITION, SENTIMENT_ANALYSIS
        "symbol": "BANKNIFTY",
        "confidence": 0.78,
        "analysis": {
            "market_sentiment": "BULLISH",
            "key_factors": [
                "Strong institutional buying",
                "Technical breakout confirmed",
                "Positive news sentiment"
            ],
            "predicted_direction": "UP",
            "predicted_magnitude": 2.5, // % change
            "prediction_horizon": 60, // minutes
            "risk_factors": [
                "Overbought RSI levels",
                "Resistance at 45200 level"
            ]
        },
        "reasoning": "Multiple technical indicators showing bullish convergence. AI model detects 78% probability of upward movement based on similar historical patterns.",
        "training_context": {
            "model_version": "gemma3_v1.2",
            "training_accuracy": 0.84,
            "similar_patterns_found": 23
        }
    }
}
```

### 5. Portfolio Updates Stream
Real-time portfolio and position updates

```json
{
    "type": "portfolio_update",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "update_type": "POSITION_CHANGE", // TRADE_EXECUTED, PNL_UPDATE, RISK_CHANGE
        "portfolio_summary": {
            "total_value": 125000.75,
            "total_pnl": 25000.75,
            "daily_pnl": 1250.50,
            "margin_used": 75000.00,
            "available_margin": 50000.75,
            "positions_count": 3
        },
        "position_updates": [
            {
                "symbol": "HDFCBANK",
                "quantity": 50,
                "average_price": 1650.25,
                "current_price": 1655.75,
                "unrealized_pnl": 275.00,
                "change_type": "PRICE_UPDATE"
            }
        ],
        "risk_metrics": {
            "daily_var": 5000.00,
            "current_drawdown": 0.02,
            "risk_violations": []
        }
    }
}
```

### 6. System Alerts Stream
System status and error notifications

```json
{
    "type": "system_alert",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "alert_id": "alert_uuid",
        "severity": "WARNING", // INFO, WARNING, ERROR, CRITICAL
        "category": "API_CONNECTION", // TRADING, SYSTEM, RISK, COMPLIANCE
        "title": "Angel One API Connection Issues",
        "message": "Intermittent connection issues detected with Angel One API. Switching to backup connection.",
        "affected_services": ["execution_engine"],
        "action_taken": "FAILOVER_TO_BACKUP",
        "requires_action": false,
        "metadata": {
            "error_code": "API_TIMEOUT",
            "retry_count": 3,
            "last_successful_connection": "2025-09-17T10:28:30Z"
        }
    }
}
```

## Interactive Commands

### Trade Request via WebSocket
```json
// Client → Server
{
    "type": "trade_request",
    "correlation_id": "req_uuid_123",
    "data": {
        "symbol": "BANKNIFTY",
        "trade_type": "BUY",
        "quantity": 25,
        "price": 45165.50, // optional for limit order
        "stop_loss": 45100.00,
        "take_profit": 45250.00,
        "strategy_id": "strategy_uuid" // optional
    }
}

// Server → Client (Response)
{
    "type": "trade_execution",
    "correlation_id": "req_uuid_123",
    "timestamp": "2025-09-17T10:30:05Z",
    "data": {
        "status": "SUBMITTED",
        "trade_id": "trade_uuid",
        "broker_order_id": "AOB123457",
        "message": "Order submitted successfully"
    }
}
```

### Strategy Control
```json
// Start/Stop Strategy
{
    "type": "strategy_control",
    "correlation_id": "req_uuid_124",
    "data": {
        "action": "START", // START, STOP, PAUSE, RESUME
        "strategy_id": "strategy_uuid",
        "parameters": {
            "override_confidence_threshold": 0.8
        }
    }
}

// Response
{
    "type": "strategy_control_response",
    "correlation_id": "req_uuid_124",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "status": "SUCCESS",
        "strategy_id": "strategy_uuid",
        "new_state": "ACTIVE",
        "message": "Strategy started successfully"
    }
}
```

## Error Handling

### Error Message Format
```json
{
    "type": "error",
    "timestamp": "2025-09-17T10:30:00Z",
    "data": {
        "error_code": "INVALID_SYMBOL",
        "error_message": "Symbol 'INVALID' is not supported",
        "correlation_id": "req_uuid_123", // if related to a request
        "severity": "ERROR",
        "retry_possible": false,
        "suggested_action": "Check symbol name and try again"
    }
}
```

### Common Error Codes
- `AUTHENTICATION_FAILED`: Invalid or expired JWT token
- `INSUFFICIENT_PERMISSIONS`: Action not allowed for current user
- `INVALID_SYMBOL`: Unsupported trading symbol
- `MARKET_CLOSED`: Trading not allowed outside market hours
- `RISK_LIMIT_EXCEEDED`: Trade violates risk management rules
- `BROKER_API_ERROR`: Broker API communication failure
- `INVALID_REQUEST_FORMAT`: Malformed request message
- `SUBSCRIPTION_LIMIT_EXCEEDED`: Too many active subscriptions
- `RATE_LIMIT_EXCEEDED`: Too many requests in time window

## Rate Limiting

- **Message Rate**: 100 messages per minute per connection
- **Subscription Limit**: 50 active subscriptions per connection
- **Trade Requests**: 10 per minute for live trading, unlimited for paper trading

## Data Compression

For high-frequency data streams, optional compression is supported:
- **Compression**: GZIP compression for large messages
- **Batch Updates**: Multiple market data points in single message
- **Delta Updates**: Only changed fields for position updates

## Connection Recovery

### Automatic Reconnection
```javascript
// Client-side reconnection logic
const reconnectWebSocket = () => {
    const ws = new WebSocket('ws://localhost:8000/ws?token=' + token);
    
    ws.onopen = () => {
        // Re-establish subscriptions
        ws.send(JSON.stringify({
            type: 'subscribe',
            data: { streams: savedSubscriptions }
        }));
    };
    
    ws.onclose = () => {
        // Exponential backoff reconnection
        setTimeout(reconnectWebSocket, backoffDelay);
        backoffDelay = Math.min(backoffDelay * 2, 30000);
    };
};
```

### Message Recovery
- Server maintains message buffer for 5 minutes
- Client can request missed messages after reconnection:

```json
{
    "type": "message_recovery",
    "data": {
        "last_received_timestamp": "2025-09-17T10:28:30Z",
        "stream_types": ["market_data", "trade_signals"]
    }
}
```

## Security Considerations

- **Authentication**: JWT token required for all operations
- **Authorization**: User can only access their own data
- **Rate Limiting**: Prevents abuse and DoS attacks
- **Input Validation**: All incoming messages validated
- **Audit Logging**: All WebSocket activities logged
- **Connection Limits**: Maximum 5 concurrent connections per user

## Testing and Development

### Test WebSocket Connection
```bash
# Using wscat (npm install -g wscat)
wscat -c "ws://localhost:8000/ws" 
> {"type":"auth","token":"your_jwt_token"}
< {"type":"auth_response","data":{"status":"authenticated"}}
```

### Mock Data for Development
Development mode provides simulated market data:
- Synthetic OHLCV data generation
- Simulated trade signals with random confidence
- Mock AI insights and predictions
- Controlled system alerts for testing

This WebSocket API enables real-time communication between the NIRAJ trading system and frontend applications, providing instant updates on market conditions, trading signals, AI insights, and portfolio changes.
