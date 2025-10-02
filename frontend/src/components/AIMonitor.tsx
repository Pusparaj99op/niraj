import React, { useState, useEffect, useMemo, Component, type ErrorInfo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  ScatterController,
  BubbleController,
} from 'chart.js';
import {
  Line,
  Doughnut,
} from 'react-chartjs-2';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Zap,
  BarChart3,
  Target,
  Gauge,
  RefreshCw,
  Settings,
  Filter,
  Maximize2,
  Minimize2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Play,
  Pause,
  Bell,
  BellOff,
  Cpu,
  Database,
  Wifi,
  Clock,
  PieChart,
  LineChart,
} from 'lucide-react';
import { useAIModels, useAIConfidenceMetrics, useAIModelPerformance, useWebSocket, useAIPredictions } from '../hooks/useApi';
import {
  formatCurrency,
  formatPercentage,
  formatNumber,
  formatDateTime,
  formatRelativeTime,
  formatConfidence,
  formatErrorMessage,
  getEmptyMessage,
} from '../utils/formatters';

// Error Boundary Component for comprehensive error handling
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class AIMonitorErrorBoundary extends Component<React.PropsWithChildren<object>, ErrorBoundaryState> {
  constructor(props: React.PropsWithChildren<object>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('AI Monitor Error Boundary caught an error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 m-4">
          <div className="flex items-center mb-4">
            <AlertTriangle className="w-8 h-8 text-red-600 mr-3" />
            <h2 className="text-xl font-semibold text-red-800">AI Monitor Error</h2>
          </div>
          <p className="text-red-700 mb-4">
            Something went wrong with the AI monitoring dashboard. Please refresh the page or contact support if the problem persists.
          </p>
          <div className="bg-red-100 p-3 rounded text-sm text-red-800 mb-4">
            <strong>Error:</strong> {this.state.error?.message}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-medium"
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
  ScatterController,
  BubbleController,
);

// AI System Health Component
const AISystemHealthCard: React.FC = () => {
  const { data: models, isLoading, error } = useAIModels();
  const { isConnected } = useWebSocket();

  const systemHealth = useMemo(() => {
    if (!models) return null;

    const activeModels = models.filter(m => m.is_active);
    const productionModels = models.filter(m => m.is_production_ready);
    const errorModels = models.filter(m => m.status === 'error');
    const trainingModels = models.filter(m => m.status === 'training');

    const avgAccuracy = activeModels.length > 0
      ? activeModels.reduce((sum, m) => {
          const accuracy = m.performance_metrics?.accuracy;
          return sum + (typeof accuracy === 'number' ? accuracy : 0);
        }, 0) / activeModels.length
      : 0;

    const totalPredictions = models.reduce((sum, m) => sum + m.total_predictions, 0);
    const successfulPredictions = models.reduce((sum, m) => sum + m.successful_predictions, 0);
    const overallWinRate = totalPredictions > 0 ? successfulPredictions / totalPredictions : 0;

    return {
      totalModels: models.length,
      activeModels: activeModels.length,
      productionModels: productionModels.length,
      errorModels: errorModels.length,
      trainingModels: trainingModels.length,
      avgAccuracy,
      overallWinRate,
      totalPredictions,
      systemStatus: errorModels.length > 0 ? 'degraded' : activeModels.length > 0 ? 'healthy' : 'warning'
    };
  }, [models]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load AI system health</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  if (!systemHealth) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'degraded': return 'text-yellow-600 bg-yellow-100';
      case 'warning': return 'text-orange-600 bg-orange-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />;
      case 'degraded': return <AlertTriangle className="w-4 h-4" />;
      case 'warning': return <AlertCircle className="w-4 h-4" />;
      default: return <XCircle className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">AI System Health</h3>
        <div className="flex items-center space-x-2">
          <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(systemHealth.systemStatus)}`}>
            {getStatusIcon(systemHealth.systemStatus)}
            <span className="ml-1 capitalize">{systemHealth.systemStatus}</span>
          </div>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">{systemHealth.totalModels}</p>
          <p className="text-xs text-gray-500">Total Models</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600">{systemHealth.activeModels}</p>
          <p className="text-xs text-gray-500">Active</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-blue-600">{systemHealth.productionModels}</p>
          <p className="text-xs text-gray-500">Production</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">{formatPercentage(systemHealth.avgAccuracy)}</p>
          <p className="text-xs text-gray-500">Avg Accuracy</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-900">{formatPercentage(systemHealth.overallWinRate)}</p>
          <p className="text-xs text-gray-500">Overall Win Rate</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-900">{formatNumber(systemHealth.totalPredictions)}</p>
          <p className="text-xs text-gray-500">Total Predictions</p>
        </div>
      </div>

      {(systemHealth.errorModels > 0 || systemHealth.trainingModels > 0) && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            {systemHealth.errorModels > 0 && (
              <span className="text-red-600">
                {systemHealth.errorModels} model{systemHealth.errorModels !== 1 ? 's' : ''} with errors
              </span>
            )}
            {systemHealth.trainingModels > 0 && (
              <span className="text-blue-600">
                {systemHealth.trainingModels} model{systemHealth.trainingModels !== 1 ? 's' : ''} training
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// AI Models List Component
const AIModelsListCard: React.FC = () => {
  const { data: models, isLoading, error } = useAIModels();
  const [sortBy, setSortBy] = useState<'name' | 'accuracy' | 'win_rate' | 'last_prediction'>('name');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [expandedModel, setExpandedModel] = useState<string | null>(null);

  const filteredAndSortedModels = useMemo(() => {
    if (!models) return [];

    let filtered = models;
    if (filterStatus !== 'all') {
      filtered = models.filter(m => m.status === filterStatus);
    }

    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'accuracy': {
          const aAccuracy = typeof a.performance_metrics?.accuracy === 'number' ? a.performance_metrics.accuracy : 0;
          const bAccuracy = typeof b.performance_metrics?.accuracy === 'number' ? b.performance_metrics.accuracy : 0;
          return bAccuracy - aAccuracy;
        }
        case 'win_rate': {
          return b.win_rate - a.win_rate;
        }
        case 'last_prediction': {
          const aTime = a.last_prediction_at ? new Date(a.last_prediction_at).getTime() : 0;
          const bTime = b.last_prediction_at ? new Date(b.last_prediction_at).getTime() : 0;
          return bTime - aTime;
        }
        default: {
          return a.name.localeCompare(b.name);
        }
      }
    });
  }, [models, sortBy, filterStatus]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'deployed': return 'text-green-700 bg-green-100';
      case 'training': return 'text-blue-700 bg-blue-100';
      case 'error': return 'text-red-700 bg-red-100';
      case 'validated': return 'text-purple-700 bg-purple-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load AI models</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">AI Models</h3>
        <div className="flex items-center space-x-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border rounded px-2 py-1"
            aria-label="Filter models by status"
          >
            <option value="all">All Status</option>
            <option value="deployed">Deployed</option>
            <option value="training">Training</option>
            <option value="validated">Validated</option>
            <option value="error">Error</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'name' | 'accuracy' | 'win_rate' | 'last_prediction')}
            className="text-sm border rounded px-2 py-1"
            aria-label="Sort models by"
          >
            <option value="name">Name</option>
            <option value="accuracy">Accuracy</option>
            <option value="win_rate">Win Rate</option>
            <option value="last_prediction">Last Prediction</option>
          </select>
        </div>
      </div>

      {filteredAndSortedModels.length > 0 ? (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredAndSortedModels.map((model) => (
            <div key={model.model_id} className="border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <Brain className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="font-medium text-gray-900">{model.name}</p>
                    <p className="text-sm text-gray-500">{model.model_type} v{model.version}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(model.status)}`}>
                    {model.status}
                  </div>
                  <button
                    onClick={() => setExpandedModel(expandedModel === model.model_id ? null : model.model_id)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    {expandedModel === model.model_id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Accuracy</p>
                  <p className="font-medium">{formatPercentage(typeof model.performance_metrics?.accuracy === 'number' ? model.performance_metrics.accuracy : 0)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Win Rate</p>
                  <p className="font-medium">{formatPercentage(model.win_rate)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Predictions</p>
                  <p className="font-medium">{formatNumber(model.total_predictions)}</p>
                </div>
              </div>

              {expandedModel === model.model_id && (
                <div className="mt-3 pt-3 border-t">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Sharpe Ratio</p>
                      <p className="font-medium">{model.sharpe_ratio ? formatNumber(model.sharpe_ratio, 2) : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Max Drawdown</p>
                      <p className="font-medium">{model.max_drawdown ? formatPercentage(model.max_drawdown) : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Last Trained</p>
                      <p className="font-medium">{model.last_trained_at ? formatRelativeTime(model.last_trained_at) : 'Never'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Last Prediction</p>
                      <p className="font-medium">{model.last_prediction_at ? formatRelativeTime(model.last_prediction_at) : 'Never'}</p>
                    </div>
                  </div>
                  {model.is_production_ready && (
                    <div className="mt-2 flex items-center text-green-600 text-sm">
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Production Ready
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <Brain className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{getEmptyMessage('models')}</p>
        </div>
      )}
    </div>
  );
};

// Confidence Tracking Component
const ConfidenceTrackingCard: React.FC = () => {
  const { data: confidenceMetrics, isLoading, error } = useAIConfidenceMetrics();
  const [selectedMetric, setSelectedMetric] = useState<string>('composite_confidence');

  const selectedMetricData = useMemo(() => {
    try {
      if (!confidenceMetrics) return null;
      return confidenceMetrics.find(m => m.metric_type === selectedMetric) || confidenceMetrics[0];
    } catch (err) {
      console.error('Error processing confidence metrics:', err);
      return null;
    }
  }, [confidenceMetrics, selectedMetric]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load confidence metrics</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  if (!selectedMetricData) return null;

  const confidenceInfo = formatConfidence(selectedMetricData.calibrated_confidence);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Confidence Tracking</h3>
        <select
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
          className="text-sm border rounded px-2 py-1"
          aria-label="Select confidence metric"
        >
          {confidenceMetrics?.map(metric => (
            <option key={metric.metric_type} value={metric.metric_type}>
              {metric.metric_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className={`inline-flex items-center px-3 py-2 rounded-full text-sm font-medium ${confidenceInfo.color}`}>
            <Gauge className="w-4 h-4 mr-2" />
            {formatPercentage(selectedMetricData.calibrated_confidence)}
          </div>
          <p className="text-xs text-gray-500 mt-1">Calibrated Confidence</p>
        </div>

        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">
            {formatPercentage(selectedMetricData.reliability_score)}
          </p>
          <p className="text-xs text-gray-500">Reliability Score</p>
        </div>

        <div className="text-center">
          <p className="text-2xl font-bold text-gray-900">
            {selectedMetricData.historical_accuracy.length > 0
              ? formatPercentage(
                  selectedMetricData.historical_accuracy.reduce((a, b) => a + b, 0) /
                  selectedMetricData.historical_accuracy.length
                )
              : 'N/A'
            }
          </p>
          <p className="text-xs text-gray-500">Historical Accuracy</p>
        </div>
      </div>

      {/* Simple calibration curve visualization */}
      <div className="mt-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Calibration Curve</h4>
        <div className="h-20 bg-gray-50 rounded p-2">
          <div className="flex items-end justify-between h-full">
            {selectedMetricData.calibration_curve.slice(0, 10).map((point, index) => (
              <div key={index} className="flex flex-col items-center">
                <div
                  className={`w-2 bg-blue-500 rounded-t`}
                  style={{ height: `${point.accuracy * 100}%` }}
                  title={`Confidence: ${formatPercentage(point.confidence)}, Accuracy: ${formatPercentage(point.accuracy)}`}
                ></div>
                <span className="text-xs text-gray-500 mt-1">{Math.round(point.confidence * 100)}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">Confidence vs Actual Accuracy (last 10 data points)</p>
      </div>
    </div>
  );
};

// Model Performance Chart Component
const ModelPerformanceChart: React.FC = () => {
  const { data: performance, isLoading, error } = useAIModelPerformance();
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [timeRange, setTimeRange] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  const chartData = useMemo(() => {
    try {
      if (!performance || !selectedModel) return null;

      const modelData = performance.find(p => p.model_id === selectedModel);
      if (!modelData) return null;

      switch (timeRange) {
        case 'daily':
          return modelData.daily_performance.slice(-30); // Last 30 days
        case 'weekly':
          return modelData.monthly_trends.slice(-12); // Last 12 months (weekly aggregated)
        case 'monthly':
          return modelData.monthly_trends.slice(-12);
        default:
          return modelData.daily_performance.slice(-30);
      }
    } catch (err) {
      console.error('Error processing chart data:', err);
      return null;
    }
  }, [performance, selectedModel, timeRange]);

  useEffect(() => {
    if (performance && performance.length > 0 && !selectedModel) {
      setSelectedModel(performance[0].model_id);
    }
  }, [performance, selectedModel]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load performance data</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Model Performance</h3>
        <div className="flex items-center space-x-2">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="text-sm border rounded px-2 py-1"
            aria-label="Select AI model"
          >
            {performance?.map(model => (
              <option key={model.model_id} value={model.model_id}>
                {model.model_id.split('-')[0]}...
              </option>
            ))}
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as 'daily' | 'weekly' | 'monthly')}
            className="text-sm border rounded px-2 py-1"
            aria-label="Select time range"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      {chartData && chartData.length > 0 ? (
        <div className="h-64">
          {/* Simple bar chart representation */}
          <div className="flex items-end justify-between h-full space-x-1">
            {chartData.map((point, index) => {
              const isDaily = timeRange === 'daily';
              const accuracy = isDaily ? (point as { date: string; accuracy: number; pnl: number; trades_count: number }).accuracy : (point as { month: string; accuracy_trend: number; pnl_trend: number }).accuracy_trend;
              const pnl = isDaily ? (point as { date: string; accuracy: number; pnl: number; trades_count: number }).pnl : (point as { month: string; accuracy_trend: number; pnl_trend: number }).pnl_trend;

              return (
                <div key={index} className="flex-1 flex flex-col items-center">
                  <div className="w-full flex flex-col items-center space-y-1">
                    {/* Accuracy bar */}
                    <div
                      className="w-3 bg-blue-500 rounded-t"
                      style={{ height: `${Math.max(accuracy * 50, 2)}px` }}
                      title={`Accuracy: ${formatPercentage(accuracy)}`}
                    ></div>
                    {/* P&L bar */}
                    <div
                      className={`w-3 rounded-t ${pnl >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ height: `${Math.max(Math.abs(pnl) * 10, 2)}px` }}
                      title={`P&L: ${formatCurrency(pnl)}`}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-500 mt-1 transform -rotate-45 origin-top-left">
                    {isDaily ? new Date((point as { date: string; accuracy: number; pnl: number; trades_count: number }).date).getDate() : (point as { month: string; accuracy_trend: number; pnl_trend: number }).month}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-center space-x-4 mt-2 text-xs text-gray-500">
            <div className="flex items-center">
              <div className="w-3 h-3 bg-blue-500 rounded mr-1"></div>
              Accuracy
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded mr-1"></div>
              Positive P&L
            </div>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-red-500 rounded mr-1"></div>
              Negative P&L
            </div>
          </div>
        </div>
      ) : (
        <div className="h-64 flex items-center justify-center">
          <div className="text-center">
            <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No performance data available</p>
            <p className="text-sm text-gray-400">Select a model to view performance metrics</p>
          </div>
        </div>
      )}
    </div>
  );
};

// AI Predictions Real-time Feed Component
const AIPredictionsFeed: React.FC = () => {
  const { data: predictions, isLoading, error } = useAIPredictions();
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showOnlyHighConfidence, setShowOnlyHighConfidence] = useState(true);

  const filteredPredictions = useMemo(() => {
    if (!predictions) return [];
    return predictions.predictions.filter(p =>
      !showOnlyHighConfidence || p.confidence_score >= 0.8
    ).slice(0, 10);
  }, [predictions, showOnlyHighConfidence]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load AI predictions</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">AI Predictions Feed</h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`p-1 rounded ${autoRefresh ? 'text-green-600' : 'text-gray-400'}`}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            {autoRefresh ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setShowOnlyHighConfidence(!showOnlyHighConfidence)}
            className={`p-1 rounded ${showOnlyHighConfidence ? 'text-blue-600' : 'text-gray-400'}`}
            title={showOnlyHighConfidence ? 'Show all predictions' : 'Show only high confidence'}
          >
            <Filter className="w-4 h-4" />
          </button>
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </div>
      </div>

      {filteredPredictions.length > 0 ? (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredPredictions.map((prediction) => {
            const directionInfo = {
              UP: { icon: <TrendingUp className="w-4 h-4" />, color: 'text-green-600 bg-green-100' },
              DOWN: { icon: <TrendingDown className="w-4 h-4" />, color: 'text-red-600 bg-red-100' },
              SIDEWAYS: { icon: <Activity className="w-4 h-4" />, color: 'text-yellow-600 bg-yellow-100' }
            }[prediction.predicted_direction] || { icon: <AlertCircle className="w-4 h-4" />, color: 'text-gray-600 bg-gray-100' };

            const confidenceInfo = formatConfidence(prediction.confidence_score);

            return (
              <div key={prediction.prediction_id} className="border rounded-lg p-3 bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="font-medium text-gray-900">{prediction.symbol}</span>
                    <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${directionInfo.color}`}>
                      {directionInfo.icon}
                      <span className="ml-1">{prediction.predicted_direction}</span>
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${confidenceInfo.color}`}>
                    {formatPercentage(prediction.confidence_score)}
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-2">{prediction.reasoning}</p>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Horizon: {prediction.prediction_horizon} periods</span>
                  <span>{formatRelativeTime(prediction.timestamp)}</span>
                </div>

                {prediction.was_correct !== null && (
                  <div className={`mt-2 px-2 py-1 rounded text-xs font-medium ${
                    prediction.was_correct
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {prediction.was_correct ? '✅ Correct' : '❌ Incorrect'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8">
          <Brain className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">
            {showOnlyHighConfidence ? 'No high-confidence predictions available' : 'No predictions available'}
          </p>
          {showOnlyHighConfidence && (
            <button
              onClick={() => setShowOnlyHighConfidence(false)}
              className="text-sm text-blue-600 hover:text-blue-800 mt-2"
            >
              Show all predictions
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// Advanced Analytics Dashboard Component
const AdvancedAnalyticsDashboard: React.FC = () => {
  const { data: models } = useAIModels();
  const { data: performance } = useAIModelPerformance();
  const { data: predictions } = useAIPredictions();

  const analyticsData = useMemo(() => {
    if (!models || !performance || !predictions) return null;

    // Model comparison data
    const modelComparison = models.map(model => {
      return {
        name: model.name,
        accuracy: model.performance_metrics?.accuracy || 0,
        winRate: model.win_rate,
        sharpeRatio: model.sharpe_ratio || 0,
        maxDrawdown: model.max_drawdown || 0,
        totalPredictions: model.total_predictions,
      };
    });

    // Prediction accuracy over time
    const predictionTrends = predictions?.predictions.slice(-50).map((p) => ({
      date: new Date(p.timestamp).toLocaleDateString(),
      confidence: p.confidence_score,
      wasCorrect: p.was_correct,
      accuracy: p.was_correct !== null ? (p.was_correct ? 1 : 0) : null,
    })) || [];

    // Risk metrics
    const riskMetrics = {
      totalPredictions: predictions?.predictions.length || 0,
      highConfidencePredictions: predictions?.predictions.filter(p => p.confidence_score >= 0.8).length || 0,
      correctPredictions: predictions?.predictions.filter(p => p.was_correct === true).length || 0,
      incorrectPredictions: predictions?.predictions.filter(p => p.was_correct === false).length || 0,
    };

    return {
      modelComparison,
      predictionTrends,
      riskMetrics,
    };
  }, [models, performance, predictions]);

  const modelComparisonChartData = useMemo(() => {
    if (!analyticsData?.modelComparison) return null;

    return {
      labels: analyticsData.modelComparison.map(m => m.name),
      datasets: [
        {
          label: 'Accuracy',
          data: analyticsData.modelComparison.map(m => m.accuracy),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y',
        },
        {
          label: 'Win Rate',
          data: analyticsData.modelComparison.map(m => m.winRate),
          borderColor: 'rgb(16, 185, 129)',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          yAxisID: 'y',
        },
        {
          label: 'Sharpe Ratio',
          data: analyticsData.modelComparison.map(m => m.sharpeRatio),
          borderColor: 'rgb(245, 158, 11)',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          yAxisID: 'y1',
        },
      ],
    };
  }, [analyticsData]);

  const predictionTrendsChartData = useMemo(() => {
    if (!analyticsData?.predictionTrends) return null;

    return {
      labels: analyticsData.predictionTrends.map(p => p.date),
      datasets: [
        {
          label: 'Confidence Score',
          data: analyticsData.predictionTrends.map(p => p.confidence),
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y',
        },
        {
          label: 'Prediction Accuracy',
          data: analyticsData.predictionTrends.map(p => p.accuracy).filter(a => a !== null),
          borderColor: 'rgb(16, 185, 129)',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          yAxisID: 'y1',
          spanGaps: true,
        },
      ],
    };
  }, [analyticsData]);

  const riskMetricsChartData = useMemo(() => {
    if (!analyticsData?.riskMetrics) return null;

    return {
      labels: ['Correct', 'Incorrect', 'High Confidence', 'Total'],
      datasets: [
        {
          data: [
            analyticsData.riskMetrics.correctPredictions,
            analyticsData.riskMetrics.incorrectPredictions,
            analyticsData.riskMetrics.highConfidencePredictions,
            analyticsData.riskMetrics.totalPredictions,
          ],
          backgroundColor: [
            'rgba(16, 185, 129, 0.8)',
            'rgba(239, 68, 68, 0.8)',
            'rgba(59, 130, 246, 0.8)',
            'rgba(156, 163, 175, 0.8)',
          ],
          borderColor: [
            'rgb(16, 185, 129)',
            'rgb(239, 68, 68)',
            'rgb(59, 130, 246)',
            'rgb(156, 163, 175)',
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [analyticsData]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Model Performance Comparison',
      },
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Accuracy / Win Rate',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Sharpe Ratio',
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* Model Comparison Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Model Performance Comparison</h3>
        <div className="h-80">
          {modelComparisonChartData ? (
            <Line data={modelComparisonChartData} options={chartOptions} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Loading model comparison data...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Prediction Trends */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Prediction Accuracy Trends</h3>
        <div className="h-80">
          {predictionTrendsChartData ? (
            <Line
              data={predictionTrendsChartData}
              options={{
                ...chartOptions,
                plugins: {
                  ...chartOptions.plugins,
                  title: {
                    display: true,
                    text: 'Prediction Trends Over Time',
                  },
                },
                scales: {
                  y: {
                    title: {
                      display: true,
                      text: 'Confidence Score',
                    },
                  },
                  y1: {
                    title: {
                      display: true,
                      text: 'Accuracy (0-1)',
                    },
                  },
                },
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <LineChart className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Loading prediction trends...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Risk Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64">
            {riskMetricsChartData ? (
              <Doughnut data={riskMetricsChartData} />
            ) : (
              <div className="flex items-center justify-center h-full">
                <PieChart className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Loading risk metrics...</p>
              </div>
            )}
          </div>
          <div className="space-y-4">
            {analyticsData?.riskMetrics && (
              <>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-sm font-medium">Total Predictions</span>
                  <span className="text-lg font-bold">{analyticsData.riskMetrics.totalPredictions}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-green-50 rounded">
                  <span className="text-sm font-medium">Correct Predictions</span>
                  <span className="text-lg font-bold text-green-600">{analyticsData.riskMetrics.correctPredictions}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-red-50 rounded">
                  <span className="text-sm font-medium">Incorrect Predictions</span>
                  <span className="text-lg font-bold text-red-600">{analyticsData.riskMetrics.incorrectPredictions}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-blue-50 rounded">
                  <span className="text-sm font-medium">High Confidence</span>
                  <span className="text-lg font-bold text-blue-600">{analyticsData.riskMetrics.highConfidencePredictions}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Real-time Alerts System Component
interface Alert {
  id: string;
  type: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  model?: string;
  symbol?: string;
  acknowledged: boolean;
}

const RealTimeAlertsSystem: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<Alert[]>([]);
  const [isAlertsEnabled, setIsAlertsEnabled] = useState(true);
  const [alertFilters, setAlertFilters] = useState({
    critical: true,
    warning: true,
    info: true,
  });

  // Mock alerts data - in real implementation, this would come from WebSocket
  useEffect(() => {
    const mockAlerts: Alert[] = [
      {
        id: '1',
        type: 'critical',
        title: 'Model Performance Degradation',
        message: 'Model accuracy dropped below 70% threshold',
        timestamp: new Date(Date.now() - 300000).toISOString(),
        model: 'LSTM_v2.1',
        acknowledged: false,
      },
      {
        id: '2',
        type: 'warning',
        title: 'High Risk Prediction',
        message: 'Prediction confidence below 60% for high-value trade',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        symbol: 'AAPL',
        acknowledged: false,
      },
      {
        id: '3',
        type: 'info',
        title: 'Model Retraining Completed',
        message: 'Model LSTM_v2.1 retraining completed successfully',
        timestamp: new Date(Date.now() - 900000).toISOString(),
        model: 'LSTM_v2.1',
        acknowledged: true,
      },
    ];
    setAlerts(mockAlerts.filter(a => !a.acknowledged));
    setAlertHistory(mockAlerts);
  }, []);

  const filteredAlerts = useMemo(() => {
    return alerts.filter(alert => alertFilters[alert.type as keyof typeof alertFilters]);
  }, [alerts, alertFilters]);

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.filter(a => a.id !== alertId));
    setAlertHistory(prev => prev.map(a =>
      a.id === alertId ? { ...a, acknowledged: true } : a
    ));
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'critical': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'info': return <CheckCircle className="w-5 h-5 text-blue-500" />;
      default: return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'critical': return 'border-red-200 bg-red-50';
      case 'warning': return 'border-yellow-200 bg-yellow-50';
      case 'info': return 'border-blue-200 bg-blue-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Real-time Alerts</h3>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsAlertsEnabled(!isAlertsEnabled)}
            className={`p-2 rounded ${isAlertsEnabled ? 'text-green-600' : 'text-gray-400'}`}
            title={isAlertsEnabled ? 'Disable alerts' : 'Enable alerts'}
          >
            {isAlertsEnabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
          </button>
          <div className="flex space-x-1">
            {Object.entries(alertFilters).map(([type, enabled]) => (
              <button
                key={type}
                onClick={() => setAlertFilters(prev => ({ ...prev, [type]: !prev[type as keyof typeof prev] }))}
                className={`px-2 py-1 text-xs rounded capitalize ${
                  enabled ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active Alerts */}
      <div className="mb-6">
        <h4 className="text-md font-medium text-gray-900 mb-3">Active Alerts ({filteredAlerts.length})</h4>
        {filteredAlerts.length > 0 ? (
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className={`p-4 rounded-lg border ${getAlertColor(alert.type)}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    {getAlertIcon(alert.type)}
                    <div className="flex-1">
                      <h5 className="font-medium text-gray-900">{alert.title}</h5>
                      <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                        <span>{formatRelativeTime(alert.timestamp)}</span>
                        {alert.model && <span>Model: {alert.model}</span>}
                        {alert.symbol && <span>Symbol: {alert.symbol}</span>}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className="text-gray-400 hover:text-gray-600"
                    title="Acknowledge alert"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <CheckCircle className="w-12 h-12 text-green-300 mx-auto mb-3" />
            <p className="text-gray-500">No active alerts</p>
            <p className="text-sm text-gray-400">All systems operating normally</p>
          </div>
        )}
      </div>

      {/* Alert History */}
      <div>
        <h4 className="text-md font-medium text-gray-900 mb-3">Alert History</h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {alertHistory.slice(0, 10).map((alert) => (
            <div key={alert.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div className="flex items-center space-x-3">
                {getAlertIcon(alert.type)}
                <div>
                  <p className="text-sm font-medium text-gray-900">{alert.title}</p>
                  <p className="text-xs text-gray-500">{formatRelativeTime(alert.timestamp)}</p>
                </div>
              </div>
              <div className={`px-2 py-1 text-xs rounded capitalize ${
                alert.acknowledged ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
              }`}>
                {alert.acknowledged ? 'Acknowledged' : 'Active'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// System Diagnostics Component
const SystemDiagnostics: React.FC = () => {
  const [systemMetrics, setSystemMetrics] = useState({
    cpu: 45,
    memory: 67,
    disk: 23,
    network: 89,
    apiResponseTime: 120,
    websocketLatency: 15,
    errorRate: 0.02,
    uptime: 99.9,
  });

  useEffect(() => {
    // Mock system metrics updates
    const interval = setInterval(() => {
      setSystemMetrics(prev => ({
        ...prev,
        cpu: Math.max(0, Math.min(100, prev.cpu + (Math.random() - 0.5) * 10)),
        memory: Math.max(0, Math.min(100, prev.memory + (Math.random() - 0.5) * 5)),
        network: Math.max(0, Math.min(100, prev.network + (Math.random() - 0.5) * 15)),
        apiResponseTime: Math.max(50, Math.min(500, prev.apiResponseTime + (Math.random() - 0.5) * 50)),
        websocketLatency: Math.max(5, Math.min(100, prev.websocketLatency + (Math.random() - 0.5) * 10)),
      }));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getMetricColor = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'text-red-600';
    if (value >= thresholds.warning) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getMetricBgColor = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'bg-red-500';
    if (value >= thresholds.warning) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">System Diagnostics</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* CPU Usage */}
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="2"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray={`${systemMetrics.cpu}, 100`}
                className={getMetricColor(systemMetrics.cpu, { warning: 70, critical: 90 })}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Cpu className="w-6 h-6 text-gray-600" />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-900">CPU Usage</p>
          <p className={`text-lg font-bold ${getMetricColor(systemMetrics.cpu, { warning: 70, critical: 90 })}`}>
            {formatPercentage(systemMetrics.cpu / 100)}
          </p>
        </div>

        {/* Memory Usage */}
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="2"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray={`${systemMetrics.memory}, 100`}
                className={getMetricColor(systemMetrics.memory, { warning: 80, critical: 95 })}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Database className="w-6 h-6 text-gray-600" />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-900">Memory</p>
          <p className={`text-lg font-bold ${getMetricColor(systemMetrics.memory, { warning: 80, critical: 95 })}`}>
            {formatPercentage(systemMetrics.memory / 100)}
          </p>
        </div>

        {/* Network */}
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="2"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray={`${systemMetrics.network}, 100`}
                className={getMetricColor(systemMetrics.network, { warning: 75, critical: 90 })}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Wifi className="w-6 h-6 text-gray-600" />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-900">Network</p>
          <p className={`text-lg font-bold ${getMetricColor(systemMetrics.network, { warning: 75, critical: 90 })}`}>
            {formatPercentage(systemMetrics.network / 100)}
          </p>
        </div>

        {/* API Response Time */}
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-2">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="2"
              />
              <path
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray={`${Math.min(100, (systemMetrics.apiResponseTime / 5))}, 100`}
                className={getMetricColor(systemMetrics.apiResponseTime, { warning: 200, critical: 400 })}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Clock className="w-6 h-6 text-gray-600" />
            </div>
          </div>
          <p className="text-sm font-medium text-gray-900">API Response</p>
          <p className={`text-lg font-bold ${getMetricColor(systemMetrics.apiResponseTime, { warning: 200, critical: 400 })}`}>
            {systemMetrics.apiResponseTime}ms
          </p>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h4 className="text-md font-medium text-gray-900">Performance Metrics</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-sm font-medium">WebSocket Latency</span>
              <span className={`font-bold ${getMetricColor(systemMetrics.websocketLatency, { warning: 50, critical: 100 })}`}>
                {systemMetrics.websocketLatency}ms
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-sm font-medium">Error Rate</span>
              <span className={`font-bold ${getMetricColor(systemMetrics.errorRate * 100, { warning: 1, critical: 5 })}`}>
                {formatPercentage(systemMetrics.errorRate)}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-sm font-medium">System Uptime</span>
              <span className="font-bold text-green-600">{formatPercentage(systemMetrics.uptime / 100)}</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-md font-medium text-gray-900">System Health</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Overall Health</span>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  systemMetrics.cpu < 70 && systemMetrics.memory < 80 && systemMetrics.apiResponseTime < 200
                    ? 'bg-green-500' : 'bg-yellow-500'
                }`}></div>
                <span className="text-sm font-medium">
                  {systemMetrics.cpu < 70 && systemMetrics.memory < 80 && systemMetrics.apiResponseTime < 200
                    ? 'Healthy' : 'Warning'}
                </span>
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getMetricBgColor(
                  (systemMetrics.cpu + systemMetrics.memory + systemMetrics.network) / 3,
                  { warning: 60, critical: 80 }
                )}`}
                style={{ width: `${((systemMetrics.cpu + systemMetrics.memory + systemMetrics.network) / 3)}%` }}
              ></div>
            </div>
            <p className="text-xs text-gray-500">Average system load</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main AI Monitor Component
const AIMonitor: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'models' | 'performance' | 'predictions' | 'analytics' | 'alerts' | 'diagnostics'>('overview');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'models', label: 'Models', icon: <Brain className="w-4 h-4" /> },
    { id: 'performance', label: 'Performance', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'predictions', label: 'Predictions', icon: <Target className="w-4 h-4" /> },
    { id: 'analytics', label: 'Analytics', icon: <LineChart className="w-4 h-4" /> },
    { id: 'alerts', label: 'Alerts', icon: <Bell className="w-4 h-4" /> },
    { id: 'diagnostics', label: 'Diagnostics', icon: <Cpu className="w-4 h-4" /> },
  ];

  const handleFullscreenToggle = () => {
    try {
      setIsFullscreen(!isFullscreen);
    } catch (err) {
      console.error('Error toggling fullscreen:', err);
    }
  };

  const handleRetry = () => {
    try {
      // In a real app, you might want to invalidate queries here
      window.location.reload();
    } catch (err) {
      console.error('Error during retry:', err);
    }
  };

  return (
    <AIMonitorErrorBoundary>
      <div className={`${isFullscreen ? 'fixed inset-0 z-50 bg-gray-50 p-6 overflow-auto' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Monitoring Dashboard</h2>
          <p className="text-gray-600">Advanced Self-Learning Algorithmic AI Personal Trading System</p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleFullscreenToggle}
            className="p-2 rounded-lg hover:bg-gray-100"
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
          <button
            onClick={handleRetry}
            className="p-2 rounded-lg hover:bg-gray-100 text-blue-600"
            title="Retry loading data"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <Settings className="w-5 h-5 text-gray-400 cursor-pointer hover:text-gray-600" />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as 'overview' | 'models' | 'performance' | 'predictions' | 'analytics' | 'alerts' | 'diagnostics')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AISystemHealthCard />
            <ConfidenceTrackingCard />
          </div>
        )}

        {activeTab === 'models' && (
          <div className="grid grid-cols-1 gap-6">
            <AIModelsListCard />
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="grid grid-cols-1 gap-6">
            <ModelPerformanceChart />
          </div>
        )}

        {activeTab === 'predictions' && (
          <div className="grid grid-cols-1 gap-6">
            <AIPredictionsFeed />
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="grid grid-cols-1 gap-6">
            <AdvancedAnalyticsDashboard />
          </div>
        )}

        {activeTab === 'alerts' && (
          <div className="grid grid-cols-1 gap-6">
            <RealTimeAlertsSystem />
          </div>
        )}

        {activeTab === 'diagnostics' && (
          <div className="grid grid-cols-1 gap-6">
            <SystemDiagnostics />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center space-x-4">
            <span>Last updated: {formatDateTime(new Date().toISOString())}</span>
            <span>•</span>
            <span>NIRAJ AI System v2.0</span>
          </div>
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-blue-500" />
            <span>Real-time monitoring active</span>
          </div>
        </div>
      </div>
      </div>
    </AIMonitorErrorBoundary>
  );
};

export default AIMonitor;
