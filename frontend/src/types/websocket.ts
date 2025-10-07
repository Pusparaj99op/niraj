/**
 * TypeScript types and interfaces for WebSocket communication
 * Matches the backend WebSocket server implementation
 */

// ================================
// Core WebSocket Types
// ================================

export type StreamType = 'market_data' | 'trade_signals' | 'portfolio' | 'ai_insights';

export type MessageType =
  | 'auth'
  | 'auth_response'
  | 'subscribe'
  | 'unsubscribe'
  | 'subscription_response'
  | 'market_data'
  | 'trade_signal'
  | 'portfolio_update'
  | 'ai_insight'
  | 'ping'
  | 'pong'
  | 'error';

export type ErrorCode =
  | 'INVALID_REQUEST_FORMAT'
  | 'AUTHENTICATION_FAILED'
  | 'AUTHORIZATION_FAILED'
  | 'INVALID_TOKEN'
  | 'TOKEN_EXPIRED'
  | 'CONNECTION_LIMIT_EXCEEDED'
  | 'SUBSCRIPTION_LIMIT_EXCEEDED'
  | 'INVALID_STREAM_TYPE'
  | 'MISSING_REQUIRED_PARAMS'
  | 'RATE_LIMIT_EXCEEDED'
  | 'INTERNAL_ERROR';

export type TradingMode = 'paper' | 'live';

// ================================
// WebSocket Message Interfaces
// ================================

export interface BaseMessage {
  type: MessageType;
  timestamp?: string;
}

// Authentication Messages
export interface AuthMessage extends BaseMessage {
  type: 'auth';
  token: string;
}

export interface AuthResponseMessage extends BaseMessage {
  type: 'auth_response';
  data: {
    status: 'authenticated' | 'failed';
    user_id?: string;
    trading_mode?: TradingMode;
    session_id?: string;
    error?: string;
  };
}

// Subscription Messages
export interface SubscribeMessage extends BaseMessage {
  type: 'subscribe';
  data: {
    streams: StreamConfig[];
  };
}

export interface UnsubscribeMessage extends BaseMessage {
  type: 'unsubscribe';
  data: {
    subscription_ids: string[];
  };
}

export interface SubscriptionResponseMessage extends BaseMessage {
  type: 'subscription_response';
  data: {
    status: 'success' | 'failed';
    active_subscriptions?: Array<{
      subscription_id: string;
      stream_type: StreamType;
    }>;
    failed_subscriptions?: Array<{
      stream_type?: StreamType;
      error: string;
    }>;
    unsubscribed?: string[];
    failed_unsubscriptions?: Array<{
      subscription_id: string;
      error: string;
    }>;
  };
}

// Ping/Pong Messages
export interface PingMessage extends BaseMessage {
  type: 'ping';
}

export interface PongMessage extends BaseMessage {
  type: 'pong';
}

// Error Messages
export interface ErrorMessage extends BaseMessage {
  type: 'error';
  data: {
    error_code: ErrorCode;
    error_message: string;
  };
}

// ================================
// Stream Configuration Interfaces
// ================================

export interface BaseStreamConfig {
  stream_type: StreamType;
}

export interface MarketDataStreamConfig extends BaseStreamConfig {
  stream_type: 'market_data';
  symbols: string[];
  timeframe: string; // '1min', '5min', '15min', '1h', '1d', etc.
}

export interface TradeSignalsStreamConfig extends BaseStreamConfig {
  stream_type: 'trade_signals';
  strategy_ids?: string[]; // Optional filter
  min_confidence?: number; // Optional minimum confidence filter
}

export interface PortfolioStreamConfig extends BaseStreamConfig {
  stream_type: 'portfolio';
  // No additional config required
}

export interface AIInsightsStreamConfig extends BaseStreamConfig {
  stream_type: 'ai_insights';
  min_confidence?: number; // Optional minimum confidence filter
}

export type StreamConfig =
  | MarketDataStreamConfig
  | TradeSignalsStreamConfig
  | PortfolioStreamConfig
  | AIInsightsStreamConfig;

// ================================
// Data Message Interfaces
// ================================

// Market Data Messages
export interface MarketDataMessage extends BaseMessage {
  type: 'market_data';
  data: {
    symbol: string;
    timeframe: string;
    ohlcv: {
      timestamp: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
      change_percent: number;
    };
    indicators: Record<string, number>;
    quote: {
      bid: number;
      ask: number;
      last_price: number;
      last_updated: string;
    };
  };
}

// Trade Signal Messages
export interface TradeSignalMessage extends BaseMessage {
  type: 'trade_signal';
  data: {
    signal_id: string;
    strategy_id: string;
    symbol: string;
    action: 'BUY' | 'SELL';
    confidence: number;
    price: number;
    quantity: number;
    timestamp: string;
    reason: string;
  };
}

// Portfolio Update Messages
export interface PortfolioUpdateMessage extends BaseMessage {
  type: 'portfolio_update';
  data: {
    user_id: string;
    total_value: number;
    total_market_value?: number;
    total_pnl: number;
    total_margin_used?: number;
    daily_pnl?: number;
    positions: Array<{
      symbol: string;
      quantity: number;
      avg_price: number;
      current_price: number;
      pnl: number;
      pnl_percentage: number;
    }>;
    cash_balance: number;
    margin_used: number;
    timestamp: string;
  };
}

// AI Insight Messages
export interface AIInsightMessage extends BaseMessage {
  type: 'ai_insight';
  data: {
    insight_id: string;
    symbol: string;
    prediction: 'UP' | 'DOWN' | 'SIDEWAYS';
    confidence: number;
    timeframe: string;
    analysis: string;
    indicators: Record<string, number>;
    timestamp: string;
  };
}

// Union type for all WebSocket messages
export type WebSocketMessage =
  | AuthMessage
  | AuthResponseMessage
  | SubscribeMessage
  | UnsubscribeMessage
  | SubscriptionResponseMessage
  | PingMessage
  | PongMessage
  | ErrorMessage
  | MarketDataMessage
  | TradeSignalMessage
  | PortfolioUpdateMessage
  | AIInsightMessage;

// ================================
// Event Handler Types
// ================================

export interface WebSocketEventHandlers {
  // Connection events
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;

  // Authentication events
  onAuthenticated?: (data: AuthResponseMessage['data']) => void;
  onAuthenticationFailed?: (error: string) => void;

  // Subscription events
  onSubscriptionResponse?: (data: SubscriptionResponseMessage['data']) => void;

  // Data events
  onMarketData?: (data: MarketDataMessage['data']) => void;
  onTradeSignal?: (data: TradeSignalMessage['data']) => void;
  onPortfolioUpdate?: (data: PortfolioUpdateMessage['data']) => void;
  onAIInsight?: (data: AIInsightMessage['data']) => void;

  // Error events
  onWebSocketError?: (error: ErrorMessage['data']) => void;

  // Connection state events
  onConnectionStateChange?: (state: WebSocketConnectionState) => void;
  onReconnectAttempt?: (attempt: number, maxAttempts: number) => void;
  onReconnectSuccess?: () => void;
  onReconnectFailed?: () => void;
}

// ================================
// Service State Types
// ================================

export type WebSocketConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'authenticated'
  | 'reconnecting'
  | 'error';

export interface WebSocketServiceState {
  connectionState: WebSocketConnectionState;
  isAuthenticated: boolean;
  activeSubscriptions: Map<string, StreamConfig>;
  lastError?: ErrorMessage['data'];
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  reconnectInterval: number;
  heartbeatInterval: number;
  lastHeartbeat?: number;
  userId?: string;
  tradingMode?: TradingMode;
  sessionId?: string;
}

// ================================
// Configuration Types
// ================================

export interface WebSocketServiceConfig {
  url: string;
  heartbeatInterval?: number; // milliseconds
  reconnectInterval?: number; // milliseconds
  maxReconnectAttempts?: number;
  authTimeout?: number; // milliseconds
  connectionTimeout?: number; // milliseconds
  enableAutoReconnect?: boolean;
  enableHeartbeat?: boolean;
  enableLogging?: boolean;
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
}

// ================================
// Utility Types
// ================================

export interface SubscriptionOptions {
  autoResubscribe?: boolean; // Resubscribe on reconnect
  retryOnError?: boolean; // Retry subscription on error
  maxRetries?: number; // Maximum retry attempts
}

export interface WebSocketMetrics {
  totalMessages: number;
  messagesPerSecond: number;
  lastMessageTime?: number;
  connectionUptime: number;
  reconnectCount: number;
  errorCount: number;
  subscriptionCount: number;
}

// ================================
// Exported Types for Consumers
// ================================

// Simplified types for component usage
export type MarketDataCallback = (data: MarketDataMessage['data']) => void;
export type TradeSignalCallback = (data: TradeSignalMessage['data']) => void;
export type PortfolioUpdateCallback = (data: PortfolioUpdateMessage['data']) => void;
export type AIInsightCallback = (data: AIInsightMessage['data']) => void;
export type ErrorCallback = (error: ErrorMessage['data']) => void;
export type ConnectionStateCallback = (state: WebSocketConnectionState) => void;

// Hook return types
export interface UseWebSocketReturn {
  connectionState: WebSocketConnectionState;
  isConnected: boolean;
  isAuthenticated: boolean;
  lastError?: ErrorMessage['data'];
  metrics: WebSocketMetrics;

  // Connection methods
  connect: (token?: string) => Promise<void>;
  disconnect: () => void;

  // Subscription methods
  subscribeToMarketData: (config: Omit<MarketDataStreamConfig, 'stream_type'>, options?: SubscriptionOptions) => Promise<string>;
  subscribeToTradeSignals: (config?: Omit<TradeSignalsStreamConfig, 'stream_type'>, options?: SubscriptionOptions) => Promise<string>;
  subscribeToPortfolio: (options?: SubscriptionOptions) => Promise<string>;
  subscribeToAIInsights: (config?: Omit<AIInsightsStreamConfig, 'stream_type'>, options?: SubscriptionOptions) => Promise<string>;
  unsubscribe: (subscriptionId: string) => Promise<void>;
  unsubscribeAll: () => Promise<void>;

  // Event handlers
  onMarketData: (callback: MarketDataCallback) => () => void;
  onTradeSignal: (callback: TradeSignalCallback) => () => void;
  onPortfolioUpdate: (callback: PortfolioUpdateCallback) => () => void;
  onAIInsight: (callback: AIInsightCallback) => () => void;
  onError: (callback: ErrorCallback) => () => void;
  onConnectionStateChange: (callback: ConnectionStateCallback) => () => void;
}
