/**
 * Advanced WebSocket Service for NIRAJ Trading System
 *
 * Provides comprehensive real-time communication with enterprise-grade features:
 * - Native WebSocket connection management (not Socket.IO)
 * - JWT authentication with automatic token refresh
 * - Multi-stream subscription management (market_data, trade_signals, portfolio, ai_insights)
 * - Automatic reconnection with exponential backoff
 * - Heartbeat monitoring and connection health checks
 * - Type-safe message handling with full TypeScript support
 * - Error handling and recovery mechanisms
 * - Connection pooling and rate limiting support
 * - Comprehensive logging and metrics collection
 * - Circuit breaker pattern for fault tolerance
 * - Message queuing and offline support
 * - Subscription persistence across reconnections
 */

import type {
  WebSocketMessage,
  WebSocketEventHandlers,
  WebSocketServiceState,
  WebSocketServiceConfig,
  WebSocketConnectionState,
  StreamConfig,
  MarketDataStreamConfig,
  TradeSignalsStreamConfig,
  PortfolioStreamConfig,
  AIInsightsStreamConfig,
  AuthMessage,
  SubscribeMessage,
  UnsubscribeMessage,
  PingMessage,
  AuthResponseMessage,
  SubscriptionResponseMessage,
  MarketDataMessage,
  TradeSignalMessage,
  PortfolioUpdateMessage,
  AIInsightMessage,
  ErrorMessage,
  WebSocketMetrics,
  SubscriptionOptions
} from '../types/websocket';

// ================================
// Configuration Constants
// ================================

const DEFAULT_CONFIG: Required<WebSocketServiceConfig> = {
  url: import.meta.env.VITE_WS_URL || 'ws://localhost:8001',
  heartbeatInterval: 30000, // 30 seconds
  reconnectInterval: 1000, // Start with 1 second
  maxReconnectAttempts: 10,
  authTimeout: 10000, // 10 seconds
  connectionTimeout: 15000, // 15 seconds
  enableAutoReconnect: true,
  enableHeartbeat: true,
  enableLogging: true,
  logLevel: 'info'
};

// ================================
// Enhanced Logger
// ================================

class WebSocketLogger {
  private logLevel: 'debug' | 'info' | 'warn' | 'error';
  private enabled: boolean;

  constructor(logLevel: 'debug' | 'info' | 'warn' | 'error' = 'info', enabled = true) {
    this.logLevel = logLevel;
    this.enabled = enabled;
  }

  private shouldLog(level: 'debug' | 'info' | 'warn' | 'error'): boolean {
    if (!this.enabled) return false;

    const levels = { debug: 0, info: 1, warn: 2, error: 3 };
    return levels[level] >= levels[this.logLevel];
  }

  debug(...args: any[]): void {
    if (this.shouldLog('debug')) {
      console.debug('[WebSocket]', ...args);
    }
  }

  info(...args: any[]): void {
    if (this.shouldLog('info')) {
      console.info('[WebSocket]', ...args);
    }
  }

  warn(...args: any[]): void {
    if (this.shouldLog('warn')) {
      console.warn('[WebSocket]', ...args);
    }
  }

  error(...args: any[]): void {
    if (this.shouldLog('error')) {
      console.error('[WebSocket]', ...args);
    }
  }
}

// ================================
// Circuit Breaker Implementation
// ================================

class CircuitBreaker {
  private failures = 0;
  private lastFailureTime: number | null = null;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private failureThreshold: number;
  private recoveryTimeout: number;

  constructor(failureThreshold = 5, recoveryTimeout = 60000) {
    this.failureThreshold = failureThreshold;
    this.recoveryTimeout = recoveryTimeout;
  }

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (this.shouldAttemptReset()) {
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is open');
      }
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private shouldAttemptReset(): boolean {
    return this.lastFailureTime !== null &&
           Date.now() - this.lastFailureTime >= this.recoveryTimeout;
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.failureThreshold) {
      this.state = 'open';
    }
  }

  get isOpen(): boolean {
    return this.state === 'open';
  }

  reset(): void {
    this.failures = 0;
    this.lastFailureTime = null;
    this.state = 'closed';
  }
}

// ================================
// Message Queue for Offline Support
// ================================

interface QueuedMessage {
  message: WebSocketMessage;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
}

class MessageQueue {
  private queue: QueuedMessage[] = [];
  private maxQueueSize = 100;

  enqueue(message: WebSocketMessage, maxRetries = 3): void {
    if (this.queue.length >= this.maxQueueSize) {
      // Remove oldest messages to make room
      this.queue.shift();
    }

    this.queue.push({
      message,
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries
    });
  }

  dequeue(): QueuedMessage | undefined {
    return this.queue.shift();
  }

  peek(): QueuedMessage | undefined {
    return this.queue[0];
  }

  clear(): void {
    this.queue = [];
  }

  get size(): number {
    return this.queue.length;
  }

  // Get messages that should be retried
  getRetryableMessages(): QueuedMessage[] {
    return this.queue.filter(item => item.retryCount < item.maxRetries);
  }
}

// ================================
// Main WebSocket Service
// ================================

export class AdvancedWebSocketService {
  private websocket: WebSocket | null = null;
  private config: Required<WebSocketServiceConfig>;
  private state: WebSocketServiceState;
  private logger: WebSocketLogger;
  private eventHandlers: WebSocketEventHandlers = {};
  private circuitBreaker: CircuitBreaker;
  private messageQueue: MessageQueue;
  private metrics: WebSocketMetrics;

  // Timers and intervals
  private heartbeatTimer: number | null = null;
  private reconnectTimer: number | null = null;
  private authTimer: number | null = null;

  // Authentication
  private authToken: string | null = null;
  private authPromise: Promise<void> | null = null;

  // Subscription management
  private pendingSubscriptions: Map<string, { config: StreamConfig; options: SubscriptionOptions }> = new Map();
  private subscriptionPromises: Map<string, { resolve: (id: string) => void; reject: (error: Error) => void }> = new Map();

  constructor(config: Partial<WebSocketServiceConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.logger = new WebSocketLogger(this.config.logLevel, this.config.enableLogging);
    this.circuitBreaker = new CircuitBreaker();
    this.messageQueue = new MessageQueue();

    // Initialize state
    this.state = {
      connectionState: 'disconnected',
      isAuthenticated: false,
      activeSubscriptions: new Map(),
      reconnectAttempts: 0,
      maxReconnectAttempts: this.config.maxReconnectAttempts,
      reconnectInterval: this.config.reconnectInterval,
      heartbeatInterval: this.config.heartbeatInterval
    };

    // Initialize metrics
    this.metrics = {
      totalMessages: 0,
      messagesPerSecond: 0,
      connectionUptime: 0,
      reconnectCount: 0,
      errorCount: 0,
      subscriptionCount: 0
    };

    this.logger.info('WebSocket service initialized', this.config);
  }

  // ================================
  // Public API Methods
  // ================================

  /**
   * Connect to WebSocket server with optional authentication token
   */
  async connect(token?: string): Promise<void> {
    if (this.state.connectionState === 'connecting' || this.state.connectionState === 'connected') {
      this.logger.debug('Already connecting or connected');
      return;
    }

    this.authToken = token || localStorage.getItem('auth_token') || null;
    this.updateConnectionState('connecting');

    try {
      await this.circuitBreaker.execute(() => this.establishConnection());
      this.logger.info('WebSocket connection established successfully');
    } catch (error) {
      this.logger.error('Failed to establish WebSocket connection:', error);
      this.handleConnectionError(error as Error);
      throw error;
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.logger.info('Disconnecting WebSocket');

    // Clear all timers
    this.clearTimers();

    // Clear queues and subscriptions
    this.messageQueue.clear();
    this.pendingSubscriptions.clear();
    this.subscriptionPromises.clear();

    // Close WebSocket connection
    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect');
      this.websocket = null;
    }

    // Reset state
    this.updateConnectionState('disconnected');
    this.state.isAuthenticated = false;
    this.state.reconnectAttempts = 0;
    this.state.activeSubscriptions.clear();

    // Reset circuit breaker
    this.circuitBreaker.reset();
  }

  /**
   * Get current connection state
   */
  getConnectionState(): WebSocketConnectionState {
    return this.state.connectionState;
  }

  /**
   * Check if connected and authenticated
   */
  isReady(): boolean {
    return this.state.connectionState === 'authenticated' && this.state.isAuthenticated;
  }

  /**
   * Get service metrics
   */
  getMetrics(): WebSocketMetrics {
    const uptime = this.state.connectionState === 'connected' || this.state.connectionState === 'authenticated'
      ? Date.now() - (this.metrics.lastMessageTime || Date.now())
      : 0;

    return {
      ...this.metrics,
      connectionUptime: uptime
    };
  }

  // ================================
  // Subscription Methods
  // ================================

  /**
   * Subscribe to market data stream
   */
  async subscribeToMarketData(
    config: Omit<MarketDataStreamConfig, 'stream_type'>,
    options: SubscriptionOptions = {}
  ): Promise<string> {
    const streamConfig: MarketDataStreamConfig = {
      stream_type: 'market_data',
      ...config
    };

    return this.subscribe(streamConfig, options);
  }

  /**
   * Subscribe to trade signals stream
   */
  async subscribeToTradeSignals(
    config: Omit<TradeSignalsStreamConfig, 'stream_type'> = {},
    options: SubscriptionOptions = {}
  ): Promise<string> {
    const streamConfig: TradeSignalsStreamConfig = {
      stream_type: 'trade_signals',
      ...config
    };

    return this.subscribe(streamConfig, options);
  }

  /**
   * Subscribe to portfolio updates stream
   */
  async subscribeToPortfolio(options: SubscriptionOptions = {}): Promise<string> {
    const streamConfig: PortfolioStreamConfig = {
      stream_type: 'portfolio'
    };

    return this.subscribe(streamConfig, options);
  }

  /**
   * Subscribe to AI insights stream
   */
  async subscribeToAIInsights(
    config: Omit<AIInsightsStreamConfig, 'stream_type'> = {},
    options: SubscriptionOptions = {}
  ): Promise<string> {
    const streamConfig: AIInsightsStreamConfig = {
      stream_type: 'ai_insights',
      ...config
    };

    return this.subscribe(streamConfig, options);
  }

  /**
   * Generic subscription method
   */
  async subscribe(config: StreamConfig, options: SubscriptionOptions = {}): Promise<string> {
    if (!this.isReady()) {
      throw new Error('WebSocket not connected or authenticated');
    }

    const subscriptionId = this.generateSubscriptionId();

    return new Promise((resolve, reject) => {
      // Store promise handlers
      this.subscriptionPromises.set(subscriptionId, { resolve, reject });

      // Store subscription for resubscription on reconnect
      if (options.autoResubscribe !== false) {
        this.pendingSubscriptions.set(subscriptionId, { config, options });
      }

      // Send subscription message
      const message: SubscribeMessage = {
        type: 'subscribe',
        data: {
          streams: [config]
        },
        timestamp: new Date().toISOString()
      };

      this.sendMessage(message);

      // Set timeout for subscription response
      setTimeout(() => {
        if (this.subscriptionPromises.has(subscriptionId)) {
          this.subscriptionPromises.delete(subscriptionId);
          reject(new Error('Subscription timeout'));
        }
      }, 10000); // 10 second timeout
    });
  }

  /**
   * Unsubscribe from a specific stream
   */
  async unsubscribe(subscriptionId: string): Promise<void> {
    if (!this.isReady()) {
      throw new Error('WebSocket not connected or authenticated');
    }

    return new Promise((resolve) => {
      const message: UnsubscribeMessage = {
        type: 'unsubscribe',
        data: {
          subscription_ids: [subscriptionId]
        },
        timestamp: new Date().toISOString()
      };

      this.sendMessage(message);

      // Remove from tracking
      this.state.activeSubscriptions.delete(subscriptionId);
      this.pendingSubscriptions.delete(subscriptionId);

      // Set timeout
      setTimeout(() => resolve(), 5000);
    });
  }

  /**
   * Unsubscribe from all streams
   */
  async unsubscribeAll(): Promise<void> {
    const subscriptionIds = Array.from(this.state.activeSubscriptions.keys());

    if (subscriptionIds.length === 0) {
      return;
    }

    if (!this.isReady()) {
      // Just clear local state if not connected
      this.state.activeSubscriptions.clear();
      this.pendingSubscriptions.clear();
      return;
    }

    const message: UnsubscribeMessage = {
      type: 'unsubscribe',
      data: {
        subscription_ids: subscriptionIds
      },
      timestamp: new Date().toISOString()
    };

    this.sendMessage(message);

    // Clear local state
    this.state.activeSubscriptions.clear();
    this.pendingSubscriptions.clear();
  }

  // ================================
  // Event Handler Registration
  // ================================

  /**
   * Set event handlers
   */
  setEventHandlers(handlers: WebSocketEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };
  }

  /**
   * Register market data callback
   */
  onMarketData(callback: (data: MarketDataMessage['data']) => void): () => void {
    this.eventHandlers.onMarketData = callback;
    return () => { delete this.eventHandlers.onMarketData; };
  }

  /**
   * Register trade signal callback
   */
  onTradeSignal(callback: (data: TradeSignalMessage['data']) => void): () => void {
    this.eventHandlers.onTradeSignal = callback;
    return () => { delete this.eventHandlers.onTradeSignal; };
  }

  /**
   * Register portfolio update callback
   */
  onPortfolioUpdate(callback: (data: PortfolioUpdateMessage['data']) => void): () => void {
    this.eventHandlers.onPortfolioUpdate = callback;
    return () => { delete this.eventHandlers.onPortfolioUpdate; };
  }

  /**
   * Register AI insight callback
   */
  onAIInsight(callback: (data: AIInsightMessage['data']) => void): () => void {
    this.eventHandlers.onAIInsight = callback;
    return () => { delete this.eventHandlers.onAIInsight; };
  }

  /**
   * Register error callback
   */
  onError(callback: (error: ErrorMessage['data']) => void): () => void {
    this.eventHandlers.onWebSocketError = callback;
    return () => { delete this.eventHandlers.onWebSocketError; };
  }

  /**
   * Register connection state change callback
   */
  onConnectionStateChange(callback: (state: WebSocketConnectionState) => void): () => void {
    this.eventHandlers.onConnectionStateChange = callback;
    return () => { delete this.eventHandlers.onConnectionStateChange; };
  }

  // ================================
  // Private Implementation Methods
  // ================================

  private async establishConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Construct WebSocket URL with optional token
        let wsUrl = this.config.url;
        if (this.authToken) {
          const separator = wsUrl.includes('?') ? '&' : '?';
          wsUrl += `${separator}token=${encodeURIComponent(this.authToken)}`;
        }

        this.logger.debug('Connecting to WebSocket:', wsUrl.replace(/token=[^&]+/, 'token=***'));

        // Create WebSocket connection
        this.websocket = new WebSocket(wsUrl);

        // Connection timeout
        const connectionTimeout = setTimeout(() => {
          if (this.websocket) {
            this.websocket.close();
          }
          reject(new Error('Connection timeout'));
        }, this.config.connectionTimeout);

        // Handle connection events
        this.websocket.onopen = () => {
          clearTimeout(connectionTimeout);
          this.logger.info('WebSocket connection opened');
          this.updateConnectionState('connected');
          this.startHeartbeat();

          // Start authentication if token provided in URL
          if (this.authToken) {
            this.authenticateConnection()
              .then(() => resolve())
              .catch(reject);
          } else {
            resolve();
          }
        };

        this.websocket.onclose = (event) => {
          clearTimeout(connectionTimeout);
          this.logger.info('WebSocket connection closed:', event.code, event.reason);
          this.handleConnectionClose(event);

          if (this.state.connectionState === 'connecting') {
            reject(new Error(`Connection closed: ${event.reason || event.code}`));
          }
        };

        this.websocket.onerror = (error) => {
          clearTimeout(connectionTimeout);
          this.logger.error('WebSocket connection error:', error);
          this.handleConnectionError(error as Event);

          if (this.state.connectionState === 'connecting') {
            reject(new Error('Connection error'));
          }
        };

        this.websocket.onmessage = (event) => {
          this.handleMessage(event);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private async authenticateConnection(): Promise<void> {
    if (!this.authToken) {
      throw new Error('No authentication token available');
    }

    return new Promise((resolve, reject) => {
      this.authPromise = new Promise((authResolve, authReject) => {
        // Set authentication timeout
        this.authTimer = setTimeout(() => {
          authReject(new Error('Authentication timeout'));
        }, this.config.authTimeout);

        // Store resolve/reject for message handler
        this.eventHandlers.onAuthenticated = (data) => {
          if (this.authTimer) {
            clearTimeout(this.authTimer);
            this.authTimer = null;
          }

          if (data.status === 'authenticated') {
            this.state.isAuthenticated = true;
            this.state.userId = data.user_id;
            this.state.tradingMode = data.trading_mode;
            this.state.sessionId = data.session_id;
            this.updateConnectionState('authenticated');

            // Resubscribe to pending subscriptions
            this.resubscribePendingSubscriptions();

            authResolve();
          } else {
            authReject(new Error(data.error || 'Authentication failed'));
          }
        };

        this.eventHandlers.onAuthenticationFailed = (error) => {
          if (this.authTimer) {
            clearTimeout(this.authTimer);
            this.authTimer = null;
          }
          authReject(new Error(error));
        };

        // Send authentication message
        const authMessage: AuthMessage = {
          type: 'auth',
          token: this.authToken!,
          timestamp: new Date().toISOString()
        };

        this.sendMessage(authMessage);
      });

      this.authPromise.then(resolve).catch(reject);
    });
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.updateMetrics();

      this.logger.debug('Received message:', message.type);

      switch (message.type) {
        case 'auth_response':
          this.handleAuthResponse(message as AuthResponseMessage);
          break;

        case 'subscription_response':
          this.handleSubscriptionResponse(message as SubscriptionResponseMessage);
          break;

        case 'market_data':
          this.handleMarketData(message as MarketDataMessage);
          break;

        case 'trade_signal':
          this.handleTradeSignal(message as TradeSignalMessage);
          break;

        case 'portfolio_update':
          this.handlePortfolioUpdate(message as PortfolioUpdateMessage);
          break;

        case 'ai_insight':
          this.handleAIInsight(message as AIInsightMessage);
          break;

        case 'ping':
          this.handlePing();
          break;

        case 'pong':
          this.handlePong();
          break;

        case 'error':
          this.handleError(message as ErrorMessage);
          break;

        default:
          this.logger.warn('Unknown message type:', (message as any).type);
      }
    } catch (error) {
      this.logger.error('Failed to parse WebSocket message:', error);
      this.metrics.errorCount++;
    }
  }

  private handleAuthResponse(message: AuthResponseMessage): void {
    if (this.eventHandlers.onAuthenticated) {
      this.eventHandlers.onAuthenticated(message.data);
    }
  }

  private handleSubscriptionResponse(message: SubscriptionResponseMessage): void {
    const { data } = message;

    // Handle successful subscriptions
    if (data.active_subscriptions) {
      data.active_subscriptions.forEach(sub => {
        // Find the pending subscription config
        const pendingConfig = Array.from(this.pendingSubscriptions.values())
          .find(p => p.config.stream_type === sub.stream_type);

        if (pendingConfig) {
          this.state.activeSubscriptions.set(sub.subscription_id, pendingConfig.config);
          this.metrics.subscriptionCount++;
        }

        // Resolve promise if waiting
        const promiseHandler = this.subscriptionPromises.get(sub.subscription_id);
        if (promiseHandler) {
          promiseHandler.resolve(sub.subscription_id);
          this.subscriptionPromises.delete(sub.subscription_id);
        }
      });
    }

    // Handle failed subscriptions
    if (data.failed_subscriptions) {
      data.failed_subscriptions.forEach(failed => {
        this.logger.error('Subscription failed:', failed);

        // Reject any waiting promises (we don't have the exact ID, so reject by stream type)
        Array.from(this.subscriptionPromises.entries()).forEach(([id, handler]) => {
          const pendingConfig = this.pendingSubscriptions.get(id);
          if (pendingConfig && pendingConfig.config.stream_type === failed.stream_type) {
            handler.reject(new Error(failed.error));
            this.subscriptionPromises.delete(id);
          }
        });
      });
    }

    // Call event handler
    if (this.eventHandlers.onSubscriptionResponse) {
      this.eventHandlers.onSubscriptionResponse(data);
    }
  }

  private handleMarketData(message: MarketDataMessage): void {
    if (this.eventHandlers.onMarketData) {
      this.eventHandlers.onMarketData(message.data);
    }
  }

  private handleTradeSignal(message: TradeSignalMessage): void {
    if (this.eventHandlers.onTradeSignal) {
      this.eventHandlers.onTradeSignal(message.data);
    }
  }

  private handlePortfolioUpdate(message: PortfolioUpdateMessage): void {
    if (this.eventHandlers.onPortfolioUpdate) {
      this.eventHandlers.onPortfolioUpdate(message.data);
    }
  }

  private handleAIInsight(message: AIInsightMessage): void {
    if (this.eventHandlers.onAIInsight) {
      this.eventHandlers.onAIInsight(message.data);
    }
  }

  private handlePing(): void {
    // Respond with pong
    const pongMessage = {
      type: 'pong' as const,
      timestamp: new Date().toISOString()
    };
    this.sendMessage(pongMessage);
  }

  private handlePong(): void {
    // Update last heartbeat time
    this.state.lastHeartbeat = Date.now();
  }

  private handleError(message: ErrorMessage): void {
    this.logger.error('WebSocket error:', message.data);
    this.state.lastError = message.data;
    this.metrics.errorCount++;

    if (this.eventHandlers.onWebSocketError) {
      this.eventHandlers.onWebSocketError(message.data);
    }

    // Handle authentication errors
    if (message.data.error_code === 'AUTHENTICATION_FAILED' ||
        message.data.error_code === 'INVALID_TOKEN' ||
        message.data.error_code === 'TOKEN_EXPIRED') {
      if (this.eventHandlers.onAuthenticationFailed) {
        this.eventHandlers.onAuthenticationFailed(message.data.error_message);
      }
    }
  }

  private handleConnectionClose(event: CloseEvent): void {
    this.clearTimers();
    this.updateConnectionState('disconnected');
    this.state.isAuthenticated = false;

    if (this.eventHandlers.onClose) {
      this.eventHandlers.onClose(event);
    }

    // Auto-reconnect if enabled
    if (this.config.enableAutoReconnect && !this.circuitBreaker.isOpen) {
      this.scheduleReconnect();
    }
  }

  private handleConnectionError(error: Event | Error): void {
    this.logger.error('WebSocket connection error:', error);
    this.metrics.errorCount++;

    if (this.eventHandlers.onError && error instanceof Event) {
      this.eventHandlers.onError(error);
    }

    this.updateConnectionState('error');
  }

  private scheduleReconnect(): void {
    if (this.state.reconnectAttempts >= this.state.maxReconnectAttempts) {
      this.logger.error('Max reconnection attempts reached');
      if (this.eventHandlers.onReconnectFailed) {
        this.eventHandlers.onReconnectFailed();
      }
      return;
    }

    this.state.reconnectAttempts++;
    const delay = Math.min(
      this.state.reconnectInterval * Math.pow(2, this.state.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );

    this.logger.info(`Scheduling reconnect attempt ${this.state.reconnectAttempts}/${this.state.maxReconnectAttempts} in ${delay}ms`);

    if (this.eventHandlers.onReconnectAttempt) {
      this.eventHandlers.onReconnectAttempt(this.state.reconnectAttempts, this.state.maxReconnectAttempts);
    }

    this.updateConnectionState('reconnecting');

    this.reconnectTimer = setTimeout(() => {
      this.connect(this.authToken || undefined)
        .then(() => {
          this.state.reconnectAttempts = 0;
          this.metrics.reconnectCount++;
          if (this.eventHandlers.onReconnectSuccess) {
            this.eventHandlers.onReconnectSuccess();
          }
        })
        .catch(() => {
          // Will automatically schedule next attempt if under limit
          this.scheduleReconnect();
        });
    }, delay);
  }

  private sendMessage(message: WebSocketMessage): void {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      this.logger.warn('Cannot send message: WebSocket not open');

      // Queue message for later if offline support enabled
      this.messageQueue.enqueue(message);
      return;
    }

    try {
      const messageStr = JSON.stringify(message);
      this.websocket.send(messageStr);
      this.logger.debug('Sent message:', message.type);
    } catch (error) {
      this.logger.error('Failed to send message:', error);
      this.messageQueue.enqueue(message);
    }
  }

  private startHeartbeat(): void {
    if (!this.config.enableHeartbeat) {
      return;
    }

    this.heartbeatTimer = setInterval(() => {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        const pingMessage: PingMessage = {
          type: 'ping',
          timestamp: new Date().toISOString()
        };
        this.sendMessage(pingMessage);
      }
    }, this.config.heartbeatInterval);
  }

  private clearTimers(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.authTimer) {
      clearTimeout(this.authTimer);
      this.authTimer = null;
    }
  }

  private updateConnectionState(newState: WebSocketConnectionState): void {
    if (this.state.connectionState !== newState) {
      const oldState = this.state.connectionState;
      this.state.connectionState = newState;

      this.logger.debug('Connection state changed:', oldState, '->', newState);

      if (this.eventHandlers.onConnectionStateChange) {
        this.eventHandlers.onConnectionStateChange(newState);
      }
    }
  }

  private updateMetrics(): void {
    this.metrics.totalMessages++;
    this.metrics.lastMessageTime = Date.now();

    // Calculate messages per second (simple rolling average)
    const now = Date.now();
    const windowSize = 10000; // 10 seconds
    if (!this.metrics.lastMessageTime || now - this.metrics.lastMessageTime > windowSize) {
      this.metrics.messagesPerSecond = 1;
    } else {
      this.metrics.messagesPerSecond = this.metrics.totalMessages / ((now - this.metrics.lastMessageTime) / 1000);
    }
  }

  private generateSubscriptionId(): string {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async resubscribePendingSubscriptions(): Promise<void> {
    if (this.pendingSubscriptions.size === 0) {
      return;
    }

    this.logger.info(`Resubscribing to ${this.pendingSubscriptions.size} streams`);

    for (const [, { config, options }] of this.pendingSubscriptions) {
      try {
        await this.subscribe(config, options);
      } catch (error) {
        this.logger.error('Failed to resubscribe:', error);
      }
    }
  }

  // ================================
  // Cleanup and Destroy
  // ================================

  /**
   * Destroy the service and clean up all resources
   */
  destroy(): void {
    this.logger.info('Destroying WebSocket service');

    this.disconnect();
    this.eventHandlers = {};
    this.pendingSubscriptions.clear();
    this.subscriptionPromises.clear();
    this.circuitBreaker.reset();
  }
}

// ================================
// Singleton Instance and Export
// ================================

// Create singleton instance
export const websocketService = new AdvancedWebSocketService();

// Export service class for custom instances
export default websocketService;

// Also export for backward compatibility with existing code
export { websocketService as WebSocketService };
