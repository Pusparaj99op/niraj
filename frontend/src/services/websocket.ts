import { io, Socket } from 'socket.io-client';
import type { MarketData, PortfolioPosition, Trade, AIPrediction } from './api';

// WebSocket event types
export interface WebSocketEvents {
  // Connection events
  connect: () => void;
  disconnect: () => void;
  connect_error: (error: Error) => void;

  // Market data events
  market_data: (data: MarketData) => void;
  market_data_batch: (data: MarketData[]) => void;

  // Portfolio events
  portfolio_update: (data: PortfolioPosition) => void;
  portfolio_summary_update: (data: { total_value: number; total_pnl: number; total_pnl_percentage: number }) => void;

  // Trade events
  trade_executed: (data: Trade) => void;
  trade_update: (data: Trade) => void;

  // Strategy events
  strategy_signal: (data: { strategy_id: string; signal: 'BUY' | 'SELL' | 'HOLD'; symbol: string; confidence: number }) => void;
  strategy_performance_update: (data: { strategy_id: string; performance: any }) => void;

  // AI events
  ai_prediction: (data: AIPrediction) => void;
  ai_insight: (data: { symbol: string; insight: string; confidence: number }) => void;

  // System events
  system_status_update: (data: { status: string; trading_mode: string; market_hours: boolean }) => void;
  system_alert: (data: { level: 'info' | 'warning' | 'error'; message: string; timestamp: string }) => void;
}

// WebSocket service class
class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private isConnecting = false;

  // Event listeners
  private eventListeners: Map<keyof WebSocketEvents, Function[]> = new Map();

  // Connection configuration
  private readonly WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'http://localhost:8000';

  constructor() {
    this.initializeEventListeners();
  }

  private initializeEventListeners(): void {
    // Initialize empty arrays for all event types
    const events: (keyof WebSocketEvents)[] = [
      'connect', 'disconnect', 'connect_error',
      'market_data', 'market_data_batch',
      'portfolio_update', 'portfolio_summary_update',
      'trade_executed', 'trade_update',
      'strategy_signal', 'strategy_performance_update',
      'ai_prediction', 'ai_insight',
      'system_status_update', 'system_alert'
    ];

    events.forEach(event => {
      this.eventListeners.set(event, []);
    });
  }

  // Connection management
  async connect(token?: string): Promise<void> {
    if (this.isConnecting || (this.socket && this.socket.connected)) {
      return;
    }

    this.isConnecting = true;

    try {
      // Get auth token from localStorage if not provided
      const authToken = token || localStorage.getItem('auth_token');

      // Create socket connection with auth
      this.socket = io(this.WS_BASE_URL, {
        transports: ['websocket', 'polling'],
        auth: authToken ? { token: authToken } : undefined,
        timeout: 5000,
        forceNew: true,
      });

      // Set up event handlers
      this.setupEventHandlers();

      // Wait for connection or timeout
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.socket!.once('connect', () => {
          clearTimeout(timeout);
          resolve();
        });

        this.socket!.once('connect_error', (error) => {
          clearTimeout(timeout);
          reject(error);
        });
      });

      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      console.log('WebSocket connected successfully');

    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.handleReconnect();
    } finally {
      this.isConnecting = false;
    }
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.emit('connect');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('disconnect');

      // Attempt to reconnect unless it was intentional
      if (reason === 'io server disconnect' || reason === 'io client disconnect') {
        // Don't reconnect for intentional disconnects
        return;
      }
      this.handleReconnect();
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.emit('connect_error', error);
      this.handleReconnect();
    });

    // Data events - forward to listeners
    const dataEvents: (keyof WebSocketEvents)[] = [
      'market_data', 'market_data_batch',
      'portfolio_update', 'portfolio_summary_update',
      'trade_executed', 'trade_update',
      'strategy_signal', 'strategy_performance_update',
      'ai_prediction', 'ai_insight',
      'system_status_update', 'system_alert'
    ];

    dataEvents.forEach(event => {
      this.socket!.on(event, (data: any) => {
        this.emit(event, data);
      });
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.reconnectDelay}ms`);

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);

    // Exponential backoff
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Max 30 seconds
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.reconnectAttempts = 0;
  }

  // Event listener management
  on<K extends keyof WebSocketEvents>(event: K, listener: WebSocketEvents[K]): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.push(listener);
    }
  }

  off<K extends keyof WebSocketEvents>(event: K, listener: WebSocketEvents[K]): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit<K extends keyof WebSocketEvents>(event: K, ...args: Parameters<WebSocketEvents[K]>): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          (listener as any)(...args);
        } catch (error) {
          console.error(`Error in ${event} listener:`, error);
        }
      });
    }
  }

  // Subscription management
  subscribeToMarketData(symbols: string[]): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('subscribe_market_data', { symbols });
    }
  }

  unsubscribeFromMarketData(symbols: string[]): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('unsubscribe_market_data', { symbols });
    }
  }

  subscribeToPortfolio(): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('subscribe_portfolio');
    }
  }

  unsubscribeFromPortfolio(): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('unsubscribe_portfolio');
    }
  }

  subscribeToStrategies(strategyIds?: string[]): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('subscribe_strategies', { strategy_ids: strategyIds });
    }
  }

  unsubscribeFromStrategies(strategyIds?: string[]): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('unsubscribe_strategies', { strategy_ids: strategyIds });
    }
  }

  subscribeToAI(): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('subscribe_ai');
    }
  }

  unsubscribeFromAI(): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('unsubscribe_ai');
    }
  }

  // Connection status
  get isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  get isConnectingStatus(): boolean {
    return this.isConnecting;
  }

  // Cleanup
  destroy(): void {
    this.disconnect();
    this.eventListeners.clear();
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
export default websocketService;
