/**
 * React Hook for WebSocket Integration
 *
 * Provides a convenient React hook interface for the WebSocket service
 * with automatic cleanup, state management, and TypeScript support.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { websocketService, AdvancedWebSocketService } from '../services/websocket';
import type {
  WebSocketConnectionState,
  WebSocketMetrics,
  MarketDataStreamConfig,
  TradeSignalsStreamConfig,

  AIInsightsStreamConfig,
  MarketDataMessage,
  TradeSignalMessage,
  PortfolioUpdateMessage,
  AIInsightMessage,
  ErrorMessage,
  SubscriptionOptions,
  UseWebSocketReturn
} from '../types/websocket';

// ================================
// Hook Implementation
// ================================

export function useWebSocket(config?: {
  autoConnect?: boolean;
  token?: string;
}): UseWebSocketReturn {
  // State management
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>('disconnected');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [lastError, setLastError] = useState<ErrorMessage['data'] | undefined>();
  const [metrics, setMetrics] = useState<WebSocketMetrics>({
    totalMessages: 0,
    messagesPerSecond: 0,
    connectionUptime: 0,
    reconnectCount: 0,
    errorCount: 0,
    subscriptionCount: 0
  });

  // Event handler refs to prevent unnecessary re-renders
  const eventHandlersRef = useRef(new Map<string, Function[]>());
  const serviceRef = useRef<AdvancedWebSocketService>(websocketService);

  // Initialize service and event handlers
  useEffect(() => {
    const service = serviceRef.current;

    // Set up event handlers
    service.setEventHandlers({
      onConnectionStateChange: (state) => {
        setConnectionState(state);
        setIsAuthenticated(state === 'authenticated');
      },

      onWebSocketError: (error) => {
        setLastError(error);
      },

      onAuthenticated: (data) => {
        setIsAuthenticated(data.status === 'authenticated');
      },

      onAuthenticationFailed: (error) => {
        setLastError({
          error_code: 'AUTHENTICATION_FAILED',
          error_message: error
        });
      }
    });

    // Update metrics periodically
    const metricsInterval = setInterval(() => {
      setMetrics(service.getMetrics());
    }, 1000);

    // Auto-connect if enabled
    if (config?.autoConnect !== false) {
      service.connect(config?.token).catch((error) => {
        console.error('Auto-connect failed:', error);
      });
    }

    // Cleanup on unmount
    return () => {
      clearInterval(metricsInterval);
      if (config?.autoConnect !== false) {
        service.disconnect();
      }
    };
  }, [config?.autoConnect, config?.token]);

  // Connection methods
  const connect = useCallback(async (token?: string) => {
    await serviceRef.current.connect(token);
  }, []);

  const disconnect = useCallback(() => {
    serviceRef.current.disconnect();
  }, []);

  // Subscription methods
  const subscribeToMarketData = useCallback(async (
    config: Omit<MarketDataStreamConfig, 'stream_type'>,
    options?: SubscriptionOptions
  ): Promise<string> => {
    return serviceRef.current.subscribeToMarketData(config, options || {});
  }, []);

  const subscribeToTradeSignals = useCallback(async (
    config?: Omit<TradeSignalsStreamConfig, 'stream_type'>,
    options?: SubscriptionOptions
  ): Promise<string> => {
    return serviceRef.current.subscribeToTradeSignals(config || {}, options || {});
  }, []);

  const subscribeToPortfolio = useCallback(async (
    options?: SubscriptionOptions
  ): Promise<string> => {
    return serviceRef.current.subscribeToPortfolio(options || {});
  }, []);

  const subscribeToAIInsights = useCallback(async (
    config?: Omit<AIInsightsStreamConfig, 'stream_type'>,
    options?: SubscriptionOptions
  ): Promise<string> => {
    return serviceRef.current.subscribeToAIInsights(config || {}, options || {});
  }, []);

  const unsubscribe = useCallback(async (subscriptionId: string): Promise<void> => {
    await serviceRef.current.unsubscribe(subscriptionId);
  }, []);

  const unsubscribeAll = useCallback(async (): Promise<void> => {
    await serviceRef.current.unsubscribeAll();
  }, []);

  // Event handler registration methods
  const onMarketData = useCallback((callback: (data: MarketDataMessage['data']) => void) => {
    const handlers = eventHandlersRef.current.get('marketData') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('marketData', handlers);

    // Register with service
    const unregister = serviceRef.current.onMarketData(callback);

    // Return cleanup function
    return () => {
      const currentHandlers = eventHandlersRef.current.get('marketData') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('marketData', currentHandlers);
      }
      unregister();
    };
  }, []);

  const onTradeSignal = useCallback((callback: (data: TradeSignalMessage['data']) => void) => {
    const handlers = eventHandlersRef.current.get('tradeSignal') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('tradeSignal', handlers);

    const unregister = serviceRef.current.onTradeSignal(callback);

    return () => {
      const currentHandlers = eventHandlersRef.current.get('tradeSignal') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('tradeSignal', currentHandlers);
      }
      unregister();
    };
  }, []);

  const onPortfolioUpdate = useCallback((callback: (data: PortfolioUpdateMessage['data']) => void) => {
    const handlers = eventHandlersRef.current.get('portfolioUpdate') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('portfolioUpdate', handlers);

    const unregister = serviceRef.current.onPortfolioUpdate(callback);

    return () => {
      const currentHandlers = eventHandlersRef.current.get('portfolioUpdate') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('portfolioUpdate', currentHandlers);
      }
      unregister();
    };
  }, []);

  const onAIInsight = useCallback((callback: (data: AIInsightMessage['data']) => void) => {
    const handlers = eventHandlersRef.current.get('aiInsight') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('aiInsight', handlers);

    const unregister = serviceRef.current.onAIInsight(callback);

    return () => {
      const currentHandlers = eventHandlersRef.current.get('aiInsight') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('aiInsight', currentHandlers);
      }
      unregister();
    };
  }, []);

  const onError = useCallback((callback: (error: ErrorMessage['data']) => void) => {
    const handlers = eventHandlersRef.current.get('error') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('error', handlers);

    const unregister = serviceRef.current.onError(callback);

    return () => {
      const currentHandlers = eventHandlersRef.current.get('error') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('error', currentHandlers);
      }
      unregister();
    };
  }, []);

  const onConnectionStateChange = useCallback((callback: (state: WebSocketConnectionState) => void) => {
    const handlers = eventHandlersRef.current.get('connectionState') || [];
    handlers.push(callback);
    eventHandlersRef.current.set('connectionState', handlers);

    const unregister = serviceRef.current.onConnectionStateChange(callback);

    return () => {
      const currentHandlers = eventHandlersRef.current.get('connectionState') || [];
      const index = currentHandlers.indexOf(callback);
      if (index > -1) {
        currentHandlers.splice(index, 1);
        eventHandlersRef.current.set('connectionState', currentHandlers);
      }
      unregister();
    };
  }, []);

  // Computed values
  const isConnected = connectionState === 'connected' || connectionState === 'authenticated';

  return {
    connectionState,
    isConnected,
    isAuthenticated,
    lastError,
    metrics,

    // Connection methods
    connect,
    disconnect,

    // Subscription methods
    subscribeToMarketData,
    subscribeToTradeSignals,
    subscribeToPortfolio,
    subscribeToAIInsights,
    unsubscribe,
    unsubscribeAll,

    // Event handlers
    onMarketData,
    onTradeSignal,
    onPortfolioUpdate,
    onAIInsight,
    onError,
    onConnectionStateChange
  };
}

// ================================
// Specialized Hooks
// ================================

/**
 * Hook for market data subscription with automatic management
 */
export function useMarketData(symbols: string[], timeframe = '15min', options?: {
  autoSubscribe?: boolean;
  subscriptionOptions?: SubscriptionOptions;
}) {
  const [marketData, setMarketData] = useState<Map<string, MarketDataMessage['data']>>(new Map());
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState<string | null>(null);

  const { subscribeToMarketData, unsubscribe, onMarketData, isAuthenticated } = useWebSocket({
    autoConnect: true
  });

  // Subscribe to market data when authenticated
  useEffect(() => {
    if (!isAuthenticated || !symbols.length || options?.autoSubscribe === false) {
      return;
    }

    let mounted = true;

    const subscribe = async () => {
      try {
        const id = await subscribeToMarketData(
          { symbols, timeframe },
          options?.subscriptionOptions
        );

        if (mounted) {
          setSubscriptionId(id);
          setIsSubscribed(true);
        }
      } catch (error) {
        console.error('Failed to subscribe to market data:', error);
      }
    };

    subscribe();

    return () => {
      mounted = false;
      if (subscriptionId) {
        unsubscribe(subscriptionId).catch(console.error);
      }
    };
  }, [isAuthenticated, symbols.join(','), timeframe, subscribeToMarketData, unsubscribe, options?.autoSubscribe, subscriptionId]);

  // Handle market data updates
  useEffect(() => {
    const cleanup = onMarketData((data) => {
      setMarketData(prev => new Map(prev.set(data.symbol, data)));
    });

    return cleanup;
  }, [onMarketData]);

  return {
    marketData,
    isSubscribed,
    subscriptionId
  };
}

/**
 * Hook for portfolio updates with automatic subscription
 */
export function usePortfolioUpdates(options?: {
  autoSubscribe?: boolean;
  subscriptionOptions?: SubscriptionOptions;
}) {
  const [portfolioData, setPortfolioData] = useState<PortfolioUpdateMessage['data'] | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState<string | null>(null);

  const { subscribeToPortfolio, unsubscribe, onPortfolioUpdate, isAuthenticated } = useWebSocket({
    autoConnect: true
  });

  // Subscribe to portfolio updates when authenticated
  useEffect(() => {
    if (!isAuthenticated || options?.autoSubscribe === false) {
      return;
    }

    let mounted = true;

    const subscribe = async () => {
      try {
        const id = await subscribeToPortfolio(options?.subscriptionOptions);

        if (mounted) {
          setSubscriptionId(id);
          setIsSubscribed(true);
        }
      } catch (error) {
        console.error('Failed to subscribe to portfolio updates:', error);
      }
    };

    subscribe();

    return () => {
      mounted = false;
      if (subscriptionId) {
        unsubscribe(subscriptionId).catch(console.error);
      }
    };
  }, [isAuthenticated, subscribeToPortfolio, unsubscribe, options?.autoSubscribe, subscriptionId]);

  // Handle portfolio updates
  useEffect(() => {
    const cleanup = onPortfolioUpdate((data) => {
      setPortfolioData(data);
    });

    return cleanup;
  }, [onPortfolioUpdate]);

  return {
    portfolioData,
    isSubscribed,
    subscriptionId
  };
}

/**
 * Hook for trade signals with filtering options
 */
export function useTradeSignals(options?: {
  strategyIds?: string[];
  minConfidence?: number;
  autoSubscribe?: boolean;
  subscriptionOptions?: SubscriptionOptions;
}) {
  const [tradeSignals, setTradeSignals] = useState<TradeSignalMessage['data'][]>([]);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscriptionId, setSubscriptionId] = useState<string | null>(null);

  const { subscribeToTradeSignals, unsubscribe, onTradeSignal, isAuthenticated } = useWebSocket({
    autoConnect: true
  });

  // Subscribe to trade signals when authenticated
  useEffect(() => {
    if (!isAuthenticated || options?.autoSubscribe === false) {
      return;
    }

    let mounted = true;

    const subscribe = async () => {
      try {
        const id = await subscribeToTradeSignals(
          {
            strategy_ids: options?.strategyIds,
            min_confidence: options?.minConfidence
          },
          options?.subscriptionOptions
        );

        if (mounted) {
          setSubscriptionId(id);
          setIsSubscribed(true);
        }
      } catch (error) {
        console.error('Failed to subscribe to trade signals:', error);
      }
    };

    subscribe();

    return () => {
      mounted = false;
      if (subscriptionId) {
        unsubscribe(subscriptionId).catch(console.error);
      }
    };
  }, [isAuthenticated, options?.strategyIds?.join(','), options?.minConfidence, subscribeToTradeSignals, unsubscribe, options?.autoSubscribe, subscriptionId]);

  // Handle trade signal updates
  useEffect(() => {
    const cleanup = onTradeSignal((data) => {
      setTradeSignals(prev => [data, ...prev].slice(0, 100)); // Keep last 100 signals
    });

    return cleanup;
  }, [onTradeSignal]);

  return {
    tradeSignals,
    isSubscribed,
    subscriptionId,
    clearSignals: () => setTradeSignals([])
  };
}

// Export default hook
export default useWebSocket;
