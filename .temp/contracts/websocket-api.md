# WebSocket API Contracts: NIRAJ Trading System

**Version**: 1.0.0  
**Date**: 17 September 2025  
**Protocol**: WebSocket (RFC 6455)  
**Transport**: ws:// or wss://

## Connection Details

### Endpoints
- **Development**: `ws://localhost:8000/ws`
- **Production**: `wss://api.niraj-trading.com/ws`

### Authentication
- **Method**: Token-based authentication
- **Header**: `Authorization: Bearer <jwt_token>`
- **Validation**: Token validated on connection establishment
- **Reconnection**: Automatic with exponential backoff (1s, 2s, 4s, 8s, 16s max)

### Connection Limits
- **Max connections per user**: 5
- **Connection timeout**: 30 seconds (ping/pong)
- **Message size limit**: 1MB
- **Rate limit**: 100 messages/second per connection

## Message Protocol

### Message Format
All messages use JSON-RPC 2.0 format with extensions:

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "method.name",
  "params": {
    "key": "value"
  }
}
```

**Response Format**:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "data": "response data"
  },
  "error": null
}
```

**Notification Format** (server → client):
```json
{
  "jsonrpc": "2.0",
  "method": "notification.type",
  "params": {
    "data": "notification data"
  }
}
```

## Client Methods (Client → Server)

### 1. subscribe.market_data
Subscribe to real-time market data streams.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "sub-001",
  "method": "subscribe.market_data",
  "params": {
    "symbols": ["BANKNIFTY", "HDFCBANK"],
    "timeframe": "15MIN"
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "sub-001",
  "result": {
    "subscription_id": "md-12345",
    "status": "active",
    "symbols": ["BANKNIFTY", "HDFCBANK"]
  }
}
```

**Parameters**:
- `symbols`: Array of strings, required
- `timeframe`: String enum ["15MIN", "1DAY"], optional, default "15MIN"

### 2. unsubscribe.market_data
Unsubscribe from market data streams.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "unsub-001",
  "method": "unsubscribe.market_data",
  "params": {
    "subscription_id": "md-12345"
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "unsub-001",
  "result": {
    "status": "unsubscribed"
  }
}
```

### 3. subscribe.portfolio
Subscribe to portfolio updates.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "port-001",
  "method": "subscribe.portfolio",
  "params": {}
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "port-001",
  "result": {
    "subscription_id": "port-67890",
    "status": "active"
  }
}
```

### 4. subscribe.strategy_signals
Subscribe to strategy execution signals.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "strat-001",
  "method": "subscribe.strategy_signals",
  "params": {
    "strategy_ids": ["uuid-1", "uuid-2"],
    "min_confidence": 0.7
  }
}
```

**Parameters**:
- `strategy_ids`: Array of UUIDs, optional (all if not specified)
- `min_confidence`: Number 0.0-1.0, optional, default 0.5

### 5. execute_trade
Execute a trade manually via WebSocket.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "trade-001",
  "method": "execute_trade",
  "params": {
    "symbol": "BANKNIFTY",
    "quantity": 50,
    "order_type": "BUY",
    "price": 45000.00,
    "strategy_id": "uuid-strategy"
  }
}
```

**Parameters**:
- `symbol`: String, required
- `quantity`: Integer, required
- `order_type`: String enum ["BUY", "SELL"], required
- `price`: Number, optional (market order if not specified)
- `strategy_id`: UUID, optional

### 6. ping
Connection health check.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "ping-001",
  "method": "ping",
  "params": {}
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "ping-001",
  "result": {
    "pong": true,
    "timestamp": "2025-09-17T10:30:00Z"
  }
}
```

## Server Notifications (Server → Client)

### 1. market_data.update
Real-time market data updates.

```json
{
  "jsonrpc": "2.0",
  "method": "market_data.update",
  "params": {
    "symbol": "BANKNIFTY",
    "data": {
      "timestamp": "2025-09-17T10:30:00+05:30",
      "open": 44900.00,
      "high": 45100.00,
      "low": 44850.00,
      "close": 45050.00,
      "volume": 1250000,
      "change_percent": 0.15
    }
  }
}
```

### 2. portfolio.update
Portfolio status changes.

```json
{
  "jsonrpc": "2.0",
  "method": "portfolio.update",
  "params": {
    "portfolio": {
      "total_capital": 100000.00,
      "available_balance": 75000.00,
      "margin_used": 25000.00,
      "unrealized_pnl": 1250.00,
      "realized_pnl": 5000.00
    }
  }
}
```

### 3. trade.executed
Trade execution confirmation.

```json
{
  "jsonrpc": "2.0",
  "method": "trade.executed",
  "params": {
    "trade": {
      "id": "uuid-trade",
      "symbol": "BANKNIFTY",
      "quantity": 50,
      "price": 45000.00,
      "order_type": "BUY",
      "order_id": "ANGEL-12345",
      "timestamp": "2025-09-17T10:30:15+05:30",
      "status": "EXECUTED",
      "profit_loss": 0.00
    }
  }
}
```

### 4. strategy.signal
Strategy execution signal.

```json
{
  "jsonrpc": "2.0",
  "method": "strategy.signal",
  "params": {
    "strategy_id": "uuid-strategy",
    "strategy_name": "The Predator Strategy",
    "signal": "BUY",
    "symbol": "BANKNIFTY",
    "confidence_score": 0.85,
    "analysis": "Strong institutional accumulation detected",
    "risk_assessment": "Medium risk, high reward potential"
  }
}
```

### 5. ai.thinking
AI model thinking process updates.

```json
{
  "jsonrpc": "2.0",
  "method": "ai.thinking",
  "params": {
    "model": "gemma3:4b-it-q4_K_M",
    "status": "analyzing",
    "progress": 75,
    "current_task": "Evaluating market sentiment",
    "insights": [
      "Bearish divergence detected on RSI",
      "Institutional order flow suggests accumulation"
    ]
  }
}
```

### 6. system.alert
System alerts and notifications.

```json
{
  "jsonrpc": "2.0",
  "method": "system.alert",
  "params": {
    "level": "WARNING",
    "message": "API rate limit approaching",
    "details": {
      "current_usage": 85,
      "limit": 100,
      "reset_time": "2025-09-17T11:00:00Z"
    }
  }
}
```

### 7. risk.alert
Risk management alerts.

```json
{
  "jsonrpc": "2.0",
  "method": "risk.alert",
  "params": {
    "type": "PORTFOLIO_RISK",
    "severity": "HIGH",
    "message": "Portfolio exposure exceeds 80% of capital",
    "recommendations": [
      "Reduce position sizes",
      "Implement stop-loss orders",
      "Diversify across more symbols"
    ]
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {
      "details": "Missing required parameter: symbol"
    }
  }
}
```

### Standard Error Codes
- `-32700`: Parse error
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32000`: Authentication failed
- `-32001`: Authorization failed
- `-32002`: Rate limit exceeded
- `-32003`: Trading disabled

## Connection Lifecycle

### 1. Connection Establishment
1. Client connects to WebSocket endpoint
2. Server validates authentication token
3. Server sends welcome message
4. Client subscribes to desired streams

### 2. Normal Operation
1. Client sends requests/notifications
2. Server processes requests and sends responses
3. Server sends notifications for subscribed events
4. Periodic ping/pong for connection health

### 3. Connection Recovery
1. Connection lost (network issue, server restart)
2. Client attempts reconnection with exponential backoff
3. Server validates authentication on reconnection
4. Client resubscribes to previous streams
5. Server sends missed events if applicable

### 4. Graceful Shutdown
1. Client sends unsubscribe requests for all subscriptions
2. Server acknowledges unsubscriptions
3. Client closes connection
4. Server cleans up connection resources

## Performance Requirements

### Latency
- **Market data updates**: <50ms end-to-end
- **Trade execution**: <200ms
- **Strategy signals**: <100ms
- **AI analysis**: <500ms

### Throughput
- **Messages/second**: 1000+ per connection
- **Concurrent connections**: 1000+ active users
- **Data processing**: 10000+ market updates/second

### Reliability
- **Uptime**: 99.9% availability
- **Message delivery**: At-least-once delivery
- **Data consistency**: Eventual consistency with conflict resolution

## Security Considerations

### Transport Security
- WSS (WebSocket Secure) for production
- TLS 1.3 with perfect forward secrecy
- Certificate pinning recommended

### Message Security
- All messages authenticated with JWT
- Sensitive data encrypted in transit
- Input validation on all parameters

### Rate Limiting
- Per-connection rate limiting
- Burst handling with token bucket algorithm
- Progressive backoff for violations

### Audit Logging
- All messages logged with timestamps
- Sensitive data masked in logs
- Log retention: 90 days rolling