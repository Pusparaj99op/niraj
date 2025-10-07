import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';

// API Base URL - should match backend server
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API Response types
export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

// System Status Types
export interface SystemStatus {
  status: 'healthy' | 'degraded' | 'down';
  trading_mode: 'paper' | 'live';
  market_hours: boolean;
  timestamp: string;
  services: Record<string, unknown>;
  api_connections: Record<string, unknown>;
  system_metrics: Record<string, unknown>;
}

// Portfolio Types
export interface PortfolioPosition {
  portfolio_id: string;
  user_id: string;
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  position_risk: number;
  margin_used: number;
  first_entry: string;
  last_updated: string;
  associated_strategies: string[];
  is_paper_position: boolean;
  position_type: 'LONG' | 'SHORT' | 'FLAT';
  position_status: string;
  stop_loss_level?: number | null;
  take_profit_level?: number | null;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME';
  daily_pnl: number;
  max_profit: number;
  max_loss: number;
  days_held: number;
  notes?: string | null;
  created_at: string;
}

export interface PortfolioAggregateSummary {
  total_positions: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  total_pnl: number;
  total_margin_used: number;
  total_position_risk: number;
  long_positions: number;
  short_positions: number;
  winning_positions: number;
  losing_positions: number;
  risk_distribution: Record<string, number>;
  sector_allocation: Record<string, number>;
  strategy_allocation: Record<string, number>;
  daily_pnl: number;
  max_drawdown: number;
  sharpe_ratio?: number;
  win_rate?: number;
}

export interface PortfolioResponse {
  positions: PortfolioPosition[];
  summary: PortfolioAggregateSummary;
  total_positions: number;
  last_updated: string;
}

// Strategy Types
export interface Strategy {
  strategy_id: string;
  name: string;
  description: string;
  category: string;
  status: 'active' | 'inactive' | 'backtesting';
  created_at: string;
  updated_at: string;
  performance_metrics?: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
  };
}

export interface StrategiesResponse {
  strategies: Strategy[];
  total: number;
  limit: number;
  offset: number;
}

// Trade Types
export interface Trade {
  trade_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  timestamp: string;
  strategy_id?: string;
  pnl?: number;
  status: 'executed' | 'pending' | 'cancelled';
}

export interface TradesResponse {
  trades: Trade[];
  total: number;
  limit: number;
  offset: number;
}

// AI Prediction Types
export interface AIPrediction {
  prediction_id: string;
  symbol: string;
  strategy_id?: string;
  timestamp: string;
  predicted_direction: 'UP' | 'DOWN' | 'SIDEWAYS';
  confidence_score: number;
  predicted_magnitude: number;
  prediction_horizon: number;
  reasoning: string;
  market_features: Record<string, unknown>;
  was_correct?: boolean;
  trade_executed?: boolean;
}

export interface AIPredictionsResponse {
  predictions: AIPrediction[];
  total: number;
  limit: number;
  offset: number;
}

// Market Data Types
export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  change_percentage: number;
  volume: number;
  timestamp: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
}

// AI Model Types
export interface AIModel {
  model_id: string;
  name: string;
  model_type: string;
  version: string;
  status: 'created' | 'training' | 'trained' | 'validating' | 'validated' | 'deployed' | 'deprecated' | 'error' | 'archived';
  is_active: boolean;
  is_production_ready: boolean;
  performance_metrics: Record<string, unknown>;
  validation_metrics: Record<string, unknown>;
  win_rate: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  total_predictions: number;
  successful_predictions: number;
  last_prediction_at?: string;
  created_at: string;
  last_trained_at?: string;
}

// Confidence Metrics Types
export interface ConfidenceMetrics {
  metric_type: string;
  raw_confidence: number;
  calibrated_confidence: number;
  reliability_score: number;
  historical_accuracy: number[];
  calibration_curve: Array<{confidence: number, accuracy: number}>;
  last_updated: string;
}

// Model Performance Types
export interface ModelPerformance {
  model_id: string;
  daily_performance: Array<{
    date: string;
    accuracy: number;
    pnl: number;
    trades_count: number;
  }>;
  weekly_stats: {
    total_trades: number;
    win_rate: number;
    avg_pnl: number;
    sharpe_ratio: number;
    max_drawdown: number;
  };
  monthly_trends: Array<{
    month: string;
    accuracy_trend: number;
    pnl_trend: number;
  }>;
}

// API Service Class
class ApiService {
  // System endpoints
  async getSystemStatus(): Promise<SystemStatus> {
    const response: AxiosResponse<SystemStatus> = await apiClient.get('/api/v1/system/status');
    return response.data;
  }

  // Portfolio endpoints
  async getPortfolio(): Promise<PortfolioResponse> {
    const response: AxiosResponse<PortfolioResponse> = await apiClient.get('/api/v1/portfolio');
    return response.data;
  }

  // Strategy endpoints
  async getStrategies(limit = 50, offset = 0): Promise<StrategiesResponse> {
    const response: AxiosResponse<StrategiesResponse> = await apiClient.get('/api/v1/strategies', {
      params: { limit, offset }
    });
    return response.data;
  }

  async getActiveStrategies(): Promise<Strategy[]> {
    const response = await this.getStrategies(100, 0);
    return response.strategies.filter(strategy => strategy.status === 'active');
  }

  async getStrategyPerformance(strategyId: string): Promise<Record<string, unknown>> {
    const response: AxiosResponse<Record<string, unknown>> = await apiClient.get(`/api/v1/strategies/${strategyId}/performance`);
    return response.data;
  }

  async getStrategyBacktest(strategyId: string, params?: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response: AxiosResponse<Record<string, unknown>> = await apiClient.post(`/api/v1/strategies/${strategyId}/backtest`, params);
    return response.data;
  }

  // Trade endpoints
  async getRecentTrades(limit = 20, offset = 0): Promise<TradesResponse> {
    const response: AxiosResponse<TradesResponse> = await apiClient.get('/api/v1/trades', {
      params: { limit, offset }
    });
    return response.data;
  }

  // AI Prediction endpoints
  async getAIPredictions(
    symbol?: string,
    strategy_id?: string,
    min_confidence = 0.7,
    limit = 20,
    offset = 0
  ): Promise<AIPredictionsResponse> {
    const response: AxiosResponse<AIPredictionsResponse> = await apiClient.get('/api/v1/ai/predictions', {
      params: {
        symbol,
        strategy_id,
        min_confidence,
        limit,
        offset
      }
    });
    return response.data;
  }

  // AI-specific endpoints
  async getAIModels(): Promise<AIModel[]> {
    const response: AxiosResponse<AIModel[]> = await apiClient.get('/api/v1/ai/models');
    return response.data;
  }

  async getAIConfidenceMetrics(): Promise<ConfidenceMetrics[]> {
    const response: AxiosResponse<ConfidenceMetrics[]> = await apiClient.get('/api/v1/ai/confidence');
    return response.data;
  }

  async getAIModelPerformance(): Promise<ModelPerformance[]> {
    const response: AxiosResponse<ModelPerformance[]> = await apiClient.get('/api/v1/ai/performance');
    return response.data;
  }

  // Market Data endpoints (if available)
  async getMarketData(symbol: string): Promise<MarketData> {
    const response: AxiosResponse<MarketData> = await apiClient.get(`/api/v1/market-data/${symbol}`);
    return response.data;
  }

  // Authentication endpoints
  async login(credentials: { username: string; password: string }): Promise<{ token: string; user: Record<string, unknown> }> {
    const response: AxiosResponse<{ token: string; user: Record<string, unknown> }> = await apiClient.post('/api/v1/auth/login', credentials);
    return response.data;
  }

  async switchMode(pin: string): Promise<{ success: boolean; mode: string }> {
    const response: AxiosResponse<{ success: boolean; mode: string }> = await apiClient.post('/api/v1/auth/switch-mode', { pin });
    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
