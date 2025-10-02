/**
 * Backward Compatibility Layer for Legacy WebSocket Code
 *
 * This module provides a compatibility layer to bridge the gap between
 * the new native WebSocket service and existing code that expects the
 * Socket.IO-based interface.
 */

import { websocketService, AdvancedWebSocketService } from './websocket';
import type {
  MarketDataMessage,
  TradeSignalMessage,
  PortfolioUpdateMessage,
  AIInsightMessage
} from '../types/websocket';

// Legacy event types for compatibility
interface LegacyWebSocketEvents {
  // Connection events
  connect: () => void;
  disconnect: () => void;
  connect_error: (error: Error) => void;

  // Market data events
  market_data: (data: Record<string, unknown>) => void;
  market_data_batch: (data: Record<string, unknown>[]) => void;

  // Portfolio events
  portfolio_update: (data: Record<string, unknown>) => void;
  portfolio_summary_update: (data: { total_value: number; total_pnl: number; total_pnl_percentage: number }) => void;

  // Trade events
  trade_executed: (data: Record<string, unknown>) => void;
  trade_update: (data: Record<string, unknown>) => void;

  // Strategy events
  strategy_signal: (data: { strategy_id: string; signal: 'BUY' | 'SELL' | 'HOLD'; symbol: string; confidence: number }) => void;
  strategy_performance_update: (data: { strategy_id: string; performance: Record<string, unknown> }) => void;

  // AI events
  ai_prediction: (data: Record<string, unknown>) => void;
  ai_insight: (data: { symbol: string; insight: string; confidence: number }) => void;

  // System events
  system_status_update: (data: { status: string; trading_mode: string; market_hours: boolean }) => void;
  system_alert: (data: { level: 'info' | 'warning' | 'error'; message: string; timestamp: string }) => void;
}

/**
 * Legacy WebSocket Service Wrapper
 *
 * Provides Socket.IO-like interface for backward compatibility
 */
class LegacyWebSocketWrapper {
  private service: AdvancedWebSocketService;
  // eslint-disable-next-line @typescript-eslint/no-unsafe-function-type
  private eventListeners: Map<keyof LegacyWebSocketEvents, Function[]> = new Map();
  private subscriptions: Map<string, string> = new Map(); // subscription type -> subscription id

  constructor(service: AdvancedWebSocketService) {
    this.service = service;
    this.initializeEventListeners();
    this.setupServiceEventHandlers();
  }

  private initializeEventListeners(): void {
    const events: (keyof LegacyWebSocketEvents)[] = [
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

  private setupServiceEventHandlers(): void {
    // Map new service events to legacy events
    this.service.setEventHandlers({
      onOpen: () => this.emit('connect'),
      onClose: () => this.emit('disconnect'),
      onError: (error) => this.emit('connect_error', new Error(error.toString())),

      onMarketData: (data) => {
        this.emit('market_data', this.transformMarketData(data));
      },

      onTradeSignal: (data) => {
        this.emit('strategy_signal', this.transformTradeSignal(data));
      },

      onPortfolioUpdate: (data) => {
        this.emit('portfolio_update', this.transformPortfolioUpdate(data));
        this.emit('portfolio_summary_update', {
          total_value: data.total_value,
          total_pnl: data.total_pnl,
          total_pnl_percentage: (data.total_pnl / data.total_value) * 100
        });
      },

      onAIInsight: (data) => {
        this.emit('ai_prediction', this.transformAIInsight(data));
      }
    });
  }

  // Data transformation methods
  private transformMarketData(data: MarketDataMessage['data']): Record<string, unknown> {
    return {
      symbol: data.symbol,
      price: data.ohlcv.close,
      change: data.ohlcv.close - data.ohlcv.open,
      change_percentage: data.ohlcv.change_percent,
      volume: data.ohlcv.volume,
      timestamp: data.ohlcv.timestamp,
      open: data.ohlcv.open,
      high: data.ohlcv.high,
      low: data.ohlcv.low,
      close: data.ohlcv.close
    };
  }

  private transformTradeSignal(data: TradeSignalMessage['data']): { strategy_id: string; signal: 'BUY' | 'SELL' | 'HOLD'; symbol: string; confidence: number } {
    return {
      strategy_id: data.strategy_id,
      signal: data.action as 'BUY' | 'SELL' | 'HOLD',
      symbol: data.symbol,
      confidence: data.confidence
    };
  }

  private transformPortfolioUpdate(data: PortfolioUpdateMessage['data']): Record<string, unknown> {
    return {
      portfolio_id: 'main', // Legacy field
      total_value: data.total_value,
      total_pnl: data.total_pnl,
      positions: data.positions
    };
  }

  private transformAIInsight(data: AIInsightMessage['data']): Record<string, unknown> {
    return {
      prediction_id: data.insight_id,
      symbol: data.symbol,
      strategy_id: null, // Not available in AI insights
      timestamp: data.timestamp,
      predicted_direction: data.prediction,
      confidence_score: data.confidence,
      predicted_magnitude: 0, // Not available
      prediction_horizon: 0, // Not available
      reasoning: data.analysis,
      market_features: data.indicators,
      was_correct: undefined,
      trade_executed: undefined
    };
  }

  // Legacy interface methods
  async connect(token?: string): Promise<void> {
    await this.service.connect(token);
  }

  disconnect(): void {
    this.service.disconnect();
  }

  on<K extends keyof LegacyWebSocketEvents>(event: K, listener: LegacyWebSocketEvents[K]): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.push(listener);
    }
  }

  off<K extends keyof LegacyWebSocketEvents>(event: K, listener: LegacyWebSocketEvents[K]): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit<K extends keyof LegacyWebSocketEvents>(event: K, ...args: Parameters<LegacyWebSocketEvents[K]>): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          (listener as (...args: unknown[]) => void)(...args);
        } catch (error) {
          console.error(`Error in legacy ${event} listener:`, error);
        }
      });
    }
  }

  // Legacy subscription methods
  async subscribeToMarketData(params: { symbols: string[] }): Promise<void> {
    try {
      const subscriptionId = await this.service.subscribeToMarketData({
        symbols: params.symbols,
        timeframe: '15min' // Default timeframe
      });
      this.subscriptions.set('market_data', subscriptionId);
    } catch (error) {
      console.error('Failed to subscribe to market data:', error);
    }
  }

  async unsubscribeFromMarketData(): Promise<void> {
    const subscriptionId = this.subscriptions.get('market_data');
    if (subscriptionId) {
      try {
        await this.service.unsubscribe(subscriptionId);
        this.subscriptions.delete('market_data');
      } catch (error) {
        console.error('Failed to unsubscribe from market data:', error);
      }
    }
  }

  async subscribeToPortfolio(): Promise<void> {
    try {
      const subscriptionId = await this.service.subscribeToPortfolio();
      this.subscriptions.set('portfolio', subscriptionId);
    } catch (error) {
      console.error('Failed to subscribe to portfolio:', error);
    }
  }

  async unsubscribeFromPortfolio(): Promise<void> {
    const subscriptionId = this.subscriptions.get('portfolio');
    if (subscriptionId) {
      try {
        await this.service.unsubscribe(subscriptionId);
        this.subscriptions.delete('portfolio');
      } catch (error) {
        console.error('Failed to unsubscribe from portfolio:', error);
      }
    }
  }

  async subscribeToStrategies(_params?: { strategy_ids?: string[] }): Promise<void> {
    try {
      const subscriptionId = await this.service.subscribeToTradeSignals({
        strategy_ids: _params?.strategy_ids
      });
      this.subscriptions.set('strategies', subscriptionId);
    } catch (error) {
      console.error('Failed to subscribe to strategies:', error);
    }
  }

  async unsubscribeFromStrategies(): Promise<void> {
    const subscriptionId = this.subscriptions.get('strategies');
    if (subscriptionId) {
      try {
        await this.service.unsubscribe(subscriptionId);
        this.subscriptions.delete('strategies');
      } catch (error) {
        console.error('Failed to unsubscribe from strategies:', error);
      }
    }
  }

  async subscribeToAI(): Promise<void> {
    try {
      const subscriptionId = await this.service.subscribeToAIInsights();
      this.subscriptions.set('ai', subscriptionId);
    } catch (error) {
      console.error('Failed to subscribe to AI:', error);
    }
  }

  async unsubscribeFromAI(): Promise<void> {
    const subscriptionId = this.subscriptions.get('ai');
    if (subscriptionId) {
      try {
        await this.service.unsubscribe(subscriptionId);
        this.subscriptions.delete('ai');
      } catch (error) {
        console.error('Failed to unsubscribe from AI:', error);
      }
    }
  }

  // Legacy connection status properties
  get isConnected(): boolean {
    return this.service.isReady();
  }

  get isConnectingStatus(): boolean {
    return this.service.getConnectionState() === 'connecting' ||
           this.service.getConnectionState() === 'reconnecting';
  }

  // Cleanup
  destroy(): void {
    this.service.destroy();
    this.eventListeners.clear();
    this.subscriptions.clear();
  }
}

// Create legacy wrapper instance
const legacyWebSocketService = new LegacyWebSocketWrapper(websocketService);

// Export for backward compatibility
export default legacyWebSocketService;
export { legacyWebSocketService as websocketService };
