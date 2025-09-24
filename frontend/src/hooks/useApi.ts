import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, useCallback } from 'react';
import {
  apiService,
} from '../services/api';
import type {
  PortfolioResponse,
  TradesResponse,
  AIPredictionsResponse,
  Strategy,
  Trade,
  AIPrediction
} from '../services/api';
import websocketService from '../services/websocket';

// Query keys for React Query
export const QUERY_KEYS = {
  systemStatus: ['system', 'status'] as const,
  portfolio: ['portfolio'] as const,
  strategies: ['strategies'] as const,
  activeStrategies: ['strategies', 'active'] as const,
  recentTrades: ['trades', 'recent'] as const,
  aiPredictions: ['ai', 'predictions'] as const,
};

// System hooks
export const useSystemStatus = () => {
  return useQuery({
    queryKey: QUERY_KEYS.systemStatus,
    queryFn: apiService.getSystemStatus,
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
};

// Portfolio hooks
export const usePortfolio = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEYS.portfolio,
    queryFn: apiService.getPortfolio,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time data
    staleTime: 2000,
  });

  // Set up WebSocket listeners for real-time updates
  useEffect(() => {
    const handlePortfolioUpdate = (data: any) => {
      queryClient.setQueryData(QUERY_KEYS.portfolio, (oldData: PortfolioResponse | undefined) => {
        if (!oldData) return oldData;

        // Update the specific position in the portfolio
        const updatedPositions = oldData.positions.map(position =>
          position.portfolio_id === data.portfolio_id ? { ...position, ...data } : position
        );

        return {
          ...oldData,
          positions: updatedPositions,
        };
      });
    };

    const handlePortfolioSummaryUpdate = (data: any) => {
      queryClient.setQueryData(QUERY_KEYS.portfolio, (oldData: PortfolioResponse | undefined) => {
        if (!oldData) return oldData;

        return {
          ...oldData,
          summary: { ...oldData.summary, ...data },
        };
      });
    };

    websocketService.on('portfolio_update', handlePortfolioUpdate);
    websocketService.on('portfolio_summary_update', handlePortfolioSummaryUpdate);

    // Subscribe to portfolio updates
    websocketService.subscribeToPortfolio();

    return () => {
      websocketService.off('portfolio_update', handlePortfolioUpdate);
      websocketService.off('portfolio_summary_update', handlePortfolioSummaryUpdate);
      websocketService.unsubscribeFromPortfolio();
    };
  }, [queryClient]);

  return query;
};

// Strategy hooks
export const useStrategies = (limit = 50, offset = 0) => {
  return useQuery({
    queryKey: [...QUERY_KEYS.strategies, limit, offset],
    queryFn: () => apiService.getStrategies(limit, offset),
    staleTime: 30000,
  });
};

export const useActiveStrategies = () => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEYS.activeStrategies,
    queryFn: apiService.getActiveStrategies,
    refetchInterval: 10000, // Refetch every 10 seconds
    staleTime: 5000,
  });

  // Set up WebSocket listeners for strategy updates
  useEffect(() => {
    const handleStrategySignal = (_data: any) => {
      // Invalidate strategies query to refetch
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.strategies });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeStrategies });
    };

    const handleStrategyPerformanceUpdate = (data: any) => {
      // Update strategy performance in cache
      queryClient.setQueryData(QUERY_KEYS.activeStrategies, (oldData: Strategy[] | undefined) => {
        if (!oldData) return oldData;

        return oldData.map(strategy =>
          strategy.strategy_id === data.strategy_id
            ? { ...strategy, performance_metrics: data.performance }
            : strategy
        );
      });
    };

    websocketService.on('strategy_signal', handleStrategySignal);
    websocketService.on('strategy_performance_update', handleStrategyPerformanceUpdate);

    // Subscribe to strategy updates
    websocketService.subscribeToStrategies();

    return () => {
      websocketService.off('strategy_signal', handleStrategySignal);
      websocketService.off('strategy_performance_update', handleStrategyPerformanceUpdate);
      websocketService.unsubscribeFromStrategies();
    };
  }, [queryClient]);

  return query;
};

// Trade hooks
export const useRecentTrades = (limit = 20, offset = 0) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: [...QUERY_KEYS.recentTrades, limit, offset],
    queryFn: () => apiService.getRecentTrades(limit, offset),
    refetchInterval: 5000, // Refetch every 5 seconds
    staleTime: 2000,
  });

  // Set up WebSocket listeners for trade updates
  useEffect(() => {
    const handleTradeExecuted = (data: Trade) => {
      // Add new trade to the beginning of the list
      queryClient.setQueryData(
        [...QUERY_KEYS.recentTrades, limit, offset],
        (oldData: TradesResponse | undefined) => {
          if (!oldData) return oldData;

          const newTrades = [data, ...oldData.trades.slice(0, limit - 1)];
          return {
            ...oldData,
            trades: newTrades,
            total: oldData.total + 1,
          };
        }
      );
    };

    const handleTradeUpdate = (data: Trade) => {
      // Update existing trade
      queryClient.setQueryData(
        [...QUERY_KEYS.recentTrades, limit, offset],
        (oldData: TradesResponse | undefined) => {
          if (!oldData) return oldData;

          const updatedTrades = oldData.trades.map(trade =>
            trade.trade_id === data.trade_id ? { ...trade, ...data } : trade
          );

          return {
            ...oldData,
            trades: updatedTrades,
          };
        }
      );
    };

    websocketService.on('trade_executed', handleTradeExecuted);
    websocketService.on('trade_update', handleTradeUpdate);

    return () => {
      websocketService.off('trade_executed', handleTradeExecuted);
      websocketService.off('trade_update', handleTradeUpdate);
    };
  }, [queryClient, limit, offset]);

  return query;
};

// AI Prediction hooks
export const useAIPredictions = (
  symbol?: string,
  strategy_id?: string,
  min_confidence = 0.7,
  limit = 20,
  offset = 0
) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: [...QUERY_KEYS.aiPredictions, symbol, strategy_id, min_confidence, limit, offset],
    queryFn: () => apiService.getAIPredictions(symbol, strategy_id, min_confidence, limit, offset),
    refetchInterval: 15000, // Refetch every 15 seconds
    staleTime: 5000,
  });

  // Set up WebSocket listeners for AI updates
  useEffect(() => {
    const handleAIPrediction = (data: AIPrediction) => {
      // Add new prediction to the beginning of the list
      queryClient.setQueryData(
        [...QUERY_KEYS.aiPredictions, symbol, strategy_id, min_confidence, limit, offset],
        (oldData: AIPredictionsResponse | undefined) => {
          if (!oldData) return oldData;

          // Check if prediction matches filters
          const matchesSymbol = !symbol || data.symbol === symbol;
          const matchesStrategy = !strategy_id || data.strategy_id === strategy_id;
          const matchesConfidence = data.confidence_score >= min_confidence;

          if (matchesSymbol && matchesStrategy && matchesConfidence) {
            const newPredictions = [data, ...oldData.predictions.slice(0, limit - 1)];
            return {
              ...oldData,
              predictions: newPredictions,
              total: oldData.total + 1,
            };
          }

          return oldData;
        }
      );
    };

    websocketService.on('ai_prediction', handleAIPrediction);

    // Subscribe to AI updates
    websocketService.subscribeToAI();

    return () => {
      websocketService.off('ai_prediction', handleAIPrediction);
      websocketService.unsubscribeFromAI();
    };
  }, [queryClient, symbol, strategy_id, min_confidence, limit, offset]);

  return query;
};

// AI-specific hooks
export const useAIModels = () => {
  return useQuery({
    queryKey: ['ai', 'models'],
    queryFn: apiService.getAIModels,
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 15000,
  });
};

export const useAIConfidenceMetrics = () => {
  return useQuery({
    queryKey: ['ai', 'confidence'],
    queryFn: apiService.getAIConfidenceMetrics,
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000,
  });
};

export const useAIModelPerformance = () => {
  return useQuery({
    queryKey: ['ai', 'performance'],
    queryFn: apiService.getAIModelPerformance,
    refetchInterval: 300000, // Refetch every 5 minutes
    staleTime: 120000,
  });
};

// WebSocket connection hook
export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(websocketService.isConnected);
  const [isConnecting, setIsConnecting] = useState(websocketService.isConnectingStatus);

  useEffect(() => {
    const handleConnect = () => {
      setIsConnected(true);
      setIsConnecting(false);
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setIsConnecting(false);
    };

    const handleConnectError = () => {
      setIsConnected(false);
      setIsConnecting(false);
    };

    websocketService.on('connect', handleConnect);
    websocketService.on('disconnect', handleDisconnect);
    websocketService.on('connect_error', handleConnectError);

    // Try to connect if not already connected
    if (!websocketService.isConnected && !websocketService.isConnectingStatus) {
      websocketService.connect();
    }

    return () => {
      websocketService.off('connect', handleConnect);
      websocketService.off('disconnect', handleDisconnect);
      websocketService.off('connect_error', handleConnectError);
    };
  }, []);

  const connect = useCallback(async (token?: string) => {
    setIsConnecting(true);
    try {
      await websocketService.connect(token);
    } catch (error) {
      setIsConnecting(false);
      throw error;
    }
  }, []);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  return {
    isConnected,
    isConnecting,
    connect,
    disconnect,
  };
};

// Authentication hooks
export const useAuth = () => {
  const queryClient = useQueryClient();

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiService.login({ username, password }),
    onSuccess: (data) => {
      // Store token
      localStorage.setItem('auth_token', data.token);

      // Connect WebSocket with new token
      websocketService.connect(data.token);

      // Invalidate all queries to refetch with new auth
      queryClient.invalidateQueries();
    },
  });

  const switchModeMutation = useMutation({
    mutationFn: (pin: string) => apiService.switchMode(pin),
    onSuccess: () => {
      // Invalidate system status to show new mode
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.systemStatus });
    },
  });

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    websocketService.disconnect();
    queryClient.clear();
  }, [queryClient]);

  return {
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    switchMode: switchModeMutation.mutate,
    switchModeAsync: switchModeMutation.mutateAsync,
    logout,
    isLoginLoading: loginMutation.isPending,
    isSwitchModeLoading: switchModeMutation.isPending,
    loginError: loginMutation.error,
    switchModeError: switchModeMutation.error,
  };
};
