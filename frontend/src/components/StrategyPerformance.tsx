import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Brain,
  Calendar,
  ChevronDown,
  ChevronUp,
  DollarSign,
  LineChart,
  Maximize2,
  Minimize2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  PieChart,
  Target,
  Shield,
  Award,
  AlertTriangle,
  BarChart2,
  Sliders,
} from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../hooks/useApi';
import {
  formatPercentage,
  formatCompactNumber,
  formatRelativeTime,
  formatStrategyStatus,
  formatConfidence,
  formatErrorMessage,
} from '../utils/formatters';
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
  TimeScale,
  Filler,
  ArcElement,
} from 'chart.js';
import type { TooltipItem } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler,
  ArcElement
);

// Enhanced TypeScript interfaces for strategy performance
export interface StrategyPerformanceMetrics {
  strategy_id: string;
  name: string;
  category: string;
  status: 'active' | 'inactive' | 'backtesting' | 'paused' | 'error';
  description: string;
  created_at: string;
  updated_at: string;
  last_execution: string;

  // Core Performance Metrics
  total_return: number;
  total_return_percentage: number;
  annual_return: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;

  // Risk Metrics
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  max_drawdown_percentage: number;
  value_at_risk: number;
  expected_shortfall: number;
  volatility: number;
  beta: number;
  alpha: number;

  // Trading Metrics
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  consecutive_wins: number;
  consecutive_losses: number;

  // Execution Metrics
  average_execution_time: number;
  slippage: number;
  commission_paid: number;
  net_profit: number;
  gross_profit: number;

  // Advanced Analytics
  information_ratio: number;
  treynor_ratio: number;
  jensen_alpha: number;
  tracking_error: number;
  upside_capture: number;
  downside_capture: number;

  // Time-based Performance
  daily_returns: Array<{
    date: string;
    return: number;
    cumulative_return: number;
    drawdown: number;
    trades_count: number;
    volume: number;
  }>;

  monthly_performance: Array<{
    month: string;
    return: number;
    trades: number;
    win_rate: number;
    sharpe: number;
  }>;

  // Benchmarking
  benchmark_return: number;
  excess_return: number;
  benchmark_correlation: number;

  // AI-Enhanced Metrics
  ai_confidence_score: number;
  prediction_accuracy: number;
  signal_strength: number;
  market_regime_adaptation: number;

  // Risk Management
  position_sizing_efficiency: number;
  risk_adjusted_return: number;
  tail_ratio: number;
  pain_index: number;
  sterling_ratio: number;

  // Real-time Status
  is_live: boolean;
  current_positions: number;
  unrealized_pnl: number;
  deployed_capital: number;
  available_capital: number;
  leverage_ratio: number;

  // Alerts and Notifications
  alerts: Array<{
    id: string;
    type: 'warning' | 'error' | 'info' | 'success';
    message: string;
    timestamp: string;
  }>;
}

export interface StrategyComparisonData {
  strategies: StrategyPerformanceMetrics[];
  comparison_period: string;
  benchmark_data: {
    name: string;
    returns: Array<{ date: string; return: number }>;
  };
}

export interface PerformanceFilters {
  timeframe: 'day' | 'week' | 'month' | 'quarter' | 'year' | 'ytd' | 'all';
  categories: string[];
  status: string[];
  minReturn: number;
  maxDrawdown: number;
  minSharpe: number;
  minWinRate: number;
  sortBy: 'return' | 'sharpe' | 'drawdown' | 'winRate' | 'trades' | 'name';
  sortOrder: 'asc' | 'desc';
}

// Component Props
interface StrategyPerformanceProps {
  className?: string;
  showComparison?: boolean;
  selectedStrategies?: string[];
  onStrategySelect?: (strategyId: string) => void;
  compactView?: boolean;
  realTimeUpdates?: boolean;
}

// Strategy Performance Chart Component
const PerformanceChart: React.FC<{
  data: StrategyPerformanceMetrics[];
  chartType: 'line' | 'bar' | 'area';
  timeframe: string;
  showBenchmark: boolean;
}> = ({ data, chartType, timeframe, showBenchmark }) => {
  const chartData = useMemo(() => {
    if (!data.length) return null;

    const colors = [
      'rgb(59, 130, 246)', // Blue
      'rgb(16, 185, 129)', // Green
      'rgb(245, 158, 11)', // Amber
      'rgb(239, 68, 68)', // Red
      'rgb(139, 92, 246)', // Purple
      'rgb(236, 72, 153)', // Pink
      'rgb(6, 182, 212)', // Cyan
      'rgb(34, 197, 94)', // Emerald
    ];

    const datasets = data.map((strategy, index) => ({
      label: strategy.name,
      data: strategy.daily_returns.map(point => ({
        x: point.date,
        y: point.cumulative_return
      })),
      borderColor: colors[index % colors.length],
      backgroundColor: chartType === 'area'
        ? colors[index % colors.length].replace('rgb', 'rgba').replace(')', ', 0.1)')
        : colors[index % colors.length],
      fill: chartType === 'area',
      tension: 0.4,
    }));

    // Add benchmark if requested
    if (showBenchmark && data[0]?.daily_returns) {
      datasets.push({
        label: 'Benchmark (NIFTY50)',
        data: data[0].daily_returns.map(point => ({
          x: point.date,
          y: point.date === data[0].daily_returns[0].date ? 0 :
              Math.random() * 0.15 - 0.075 // Simulated benchmark data
        })),
        borderColor: 'rgb(107, 114, 128)',
        backgroundColor: 'rgba(107, 114, 128, 0.1)',
        fill: false,
        tension: 0.4,
      });
    }

    return { datasets };
  }, [data, chartType, showBenchmark]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: `Strategy Performance (${timeframe})`,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context: TooltipItem<'line' | 'bar'>) => {
            const value = context.parsed.y;
            return `${context.dataset.label || ''}: ${formatPercentage(value / 100)}`;
          },
        },
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: (timeframe === 'day' ? 'hour' : 'day') as 'hour' | 'day',
        },
        title: {
          display: true,
          text: 'Time',
        },
      },
      y: {
        title: {
          display: true,
          text: 'Cumulative Return (%)',
        },
        ticks: {
          callback: (value: string | number) => formatPercentage(Number(value) / 100),
        },
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
  };

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <LineChart className="w-8 h-8 mr-2" />
        <span>No performance data available</span>
      </div>
    );
  }

  const ChartComponent = chartType === 'bar' ? Bar : Line;

  return (
    <div className="h-64">
      <ChartComponent data={chartData} options={options} />
    </div>
  );
};

// Strategy Metrics Grid Component
const MetricsGrid: React.FC<{
  strategy: StrategyPerformanceMetrics;
  showAdvanced: boolean;
}> = ({ strategy, showAdvanced }) => {
  const metrics = [
    // Core Performance
    {
      label: 'Total Return',
      value: formatPercentage(strategy.total_return_percentage / 100),
      icon: <TrendingUp className="w-4 h-4" />,
      color: strategy.total_return >= 0 ? 'text-green-600' : 'text-red-600',
      category: 'core'
    },
    {
      label: 'Annual Return',
      value: formatPercentage(strategy.annual_return / 100),
      icon: <Calendar className="w-4 h-4" />,
      color: strategy.annual_return >= 0 ? 'text-green-600' : 'text-red-600',
      category: 'core'
    },
    {
      label: 'Sharpe Ratio',
      value: strategy.sharpe_ratio.toFixed(2),
      icon: <BarChart3 className="w-4 h-4" />,
      color: strategy.sharpe_ratio >= 1 ? 'text-green-600' : strategy.sharpe_ratio >= 0.5 ? 'text-yellow-600' : 'text-red-600',
      category: 'core'
    },
    {
      label: 'Max Drawdown',
      value: formatPercentage(strategy.max_drawdown_percentage / 100),
      icon: <TrendingDown className="w-4 h-4" />,
      color: Math.abs(strategy.max_drawdown_percentage) <= 10 ? 'text-green-600' :
             Math.abs(strategy.max_drawdown_percentage) <= 20 ? 'text-yellow-600' : 'text-red-600',
      category: 'core'
    },
    {
      label: 'Win Rate',
      value: formatPercentage(strategy.win_rate / 100),
      icon: <Target className="w-4 h-4" />,
      color: strategy.win_rate >= 60 ? 'text-green-600' : strategy.win_rate >= 50 ? 'text-yellow-600' : 'text-red-600',
      category: 'core'
    },
    {
      label: 'Total Trades',
      value: formatCompactNumber(strategy.total_trades),
      icon: <Activity className="w-4 h-4" />,
      color: 'text-blue-600',
      category: 'core'
    },

    // Advanced Metrics (shown when expanded)
    {
      label: 'Sortino Ratio',
      value: strategy.sortino_ratio.toFixed(2),
      icon: <BarChart2 className="w-4 h-4" />,
      color: strategy.sortino_ratio >= 1 ? 'text-green-600' : 'text-yellow-600',
      category: 'advanced'
    },
    {
      label: 'Calmar Ratio',
      value: strategy.calmar_ratio.toFixed(2),
      icon: <Shield className="w-4 h-4" />,
      color: strategy.calmar_ratio >= 0.5 ? 'text-green-600' : 'text-yellow-600',
      category: 'advanced'
    },
    {
      label: 'Profit Factor',
      value: strategy.profit_factor.toFixed(2),
      icon: <DollarSign className="w-4 h-4" />,
      color: strategy.profit_factor >= 1.5 ? 'text-green-600' : strategy.profit_factor >= 1 ? 'text-yellow-600' : 'text-red-600',
      category: 'advanced'
    },
    {
      label: 'Volatility',
      value: formatPercentage(strategy.volatility / 100),
      icon: <AlertTriangle className="w-4 h-4" />,
      color: strategy.volatility <= 15 ? 'text-green-600' : strategy.volatility <= 25 ? 'text-yellow-600' : 'text-red-600',
      category: 'advanced'
    },
    {
      label: 'Alpha',
      value: formatPercentage(strategy.alpha / 100),
      icon: <Award className="w-4 h-4" />,
      color: strategy.alpha >= 0 ? 'text-green-600' : 'text-red-600',
      category: 'advanced'
    },
    {
      label: 'Beta',
      value: strategy.beta.toFixed(2),
      icon: <TrendingUp className="w-4 h-4" />,
      color: 'text-blue-600',
      category: 'advanced'
    },
  ];

  const displayMetrics = showAdvanced ? metrics : metrics.filter(m => m.category === 'core');

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {displayMetrics.map((metric, index) => (
        <div key={index} className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className={`${metric.color}`}>
              {metric.icon}
            </div>
            <span className="text-xs text-gray-500 uppercase tracking-wide">
              {metric.category}
            </span>
          </div>
          <div className={`text-lg font-semibold ${metric.color}`}>
            {metric.value}
          </div>
          <div className="text-xs text-gray-600">
            {metric.label}
          </div>
        </div>
      ))}
    </div>
  );
};

// Strategy Comparison Table Component
const ComparisonTable: React.FC<{
  strategies: StrategyPerformanceMetrics[];
  onStrategySelect: (strategyId: string) => void;
  selectedStrategies: string[];
}> = ({ strategies, onStrategySelect, selectedStrategies }) => {
  const [sortBy, setSortBy] = useState<keyof StrategyPerformanceMetrics>('total_return_percentage');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const sortedStrategies = useMemo(() => {
    return [...strategies].sort((a, b) => {
      const aValue = a[sortBy] as number;
      const bValue = b[sortBy] as number;
      return sortOrder === 'desc' ? bValue - aValue : aValue - bValue;
    });
  }, [strategies, sortBy, sortOrder]);

  const handleSort = (key: keyof StrategyPerformanceMetrics) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
  };

  const SortableHeader: React.FC<{
    label: string;
    sortKey: keyof StrategyPerformanceMetrics;
  }> = ({ label, sortKey }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-50"
      onClick={() => handleSort(sortKey)}
    >
      <div className="flex items-center space-x-1">
        <span>{label}</span>
        {sortBy === sortKey && (
          sortOrder === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />
        )}
      </div>
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <input
                type="checkbox"
                className="rounded border-gray-300"
                onChange={(e) => {
                  if (e.target.checked) {
                    strategies.forEach(s => onStrategySelect(s.strategy_id));
                  } else {
                    selectedStrategies.forEach(id => onStrategySelect(id));
                  }
                }}
                checked={selectedStrategies.length === strategies.length}
                title="Select all strategies"
              />
            </th>
            <SortableHeader label="Strategy" sortKey="name" />
            <SortableHeader label="Status" sortKey="status" />
            <SortableHeader label="Return" sortKey="total_return_percentage" />
            <SortableHeader label="Sharpe" sortKey="sharpe_ratio" />
            <SortableHeader label="Drawdown" sortKey="max_drawdown_percentage" />
            <SortableHeader label="Win Rate" sortKey="win_rate" />
            <SortableHeader label="Trades" sortKey="total_trades" />
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              AI Score
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {sortedStrategies.map((strategy) => {
            const statusInfo = formatStrategyStatus(strategy.status);
            const isSelected = selectedStrategies.includes(strategy.strategy_id);

            return (
              <tr
                key={strategy.strategy_id}
                className={`hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}
              >
                <td className="px-4 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={isSelected}
                    onChange={() => onStrategySelect(strategy.strategy_id)}
                    title={`Select ${strategy.name}`}
                  />
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{strategy.name}</div>
                    <div className="text-sm text-gray-500">{strategy.category}</div>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${statusInfo.bgColor} ${statusInfo.color}`}>
                    {statusInfo.text}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className={`text-sm font-medium ${
                    strategy.total_return_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {formatPercentage(strategy.total_return_percentage / 100)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className={`text-sm ${
                    strategy.sharpe_ratio >= 1 ? 'text-green-600' :
                    strategy.sharpe_ratio >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {strategy.sharpe_ratio.toFixed(2)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className={`text-sm ${
                    Math.abs(strategy.max_drawdown_percentage) <= 10 ? 'text-green-600' :
                    Math.abs(strategy.max_drawdown_percentage) <= 20 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {formatPercentage(strategy.max_drawdown_percentage / 100)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className={`text-sm ${
                    strategy.win_rate >= 60 ? 'text-green-600' :
                    strategy.win_rate >= 50 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {formatPercentage(strategy.win_rate / 100)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    {formatCompactNumber(strategy.total_trades)}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <Brain className="w-4 h-4 text-purple-500" />
                    <span className={`text-sm ${formatConfidence(strategy.ai_confidence_score).color}`}>
                      {Math.round(strategy.ai_confidence_score * 100)}%
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// Main Strategy Performance Component
const StrategyPerformance: React.FC<StrategyPerformanceProps> = ({
  className = '',
  showComparison = true,
  selectedStrategies: initialSelectedStrategies = [],
  onStrategySelect,
  compactView = false,
  realTimeUpdates = true,
}) => {
  // State management
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(initialSelectedStrategies);
  const [filters, setFilters] = useState<PerformanceFilters>({
    timeframe: 'month',
    categories: [],
    status: ['active'],
    minReturn: -100,
    maxDrawdown: 100,
    minSharpe: 0,
    minWinRate: 0,
    sortBy: 'return',
    sortOrder: 'desc',
  });
  const [viewMode, setViewMode] = useState<'grid' | 'table' | 'chart'>('grid');
  const [chartType, setChartType] = useState<'line' | 'bar' | 'area'>('line');
  const [showAdvancedMetrics, setShowAdvancedMetrics] = useState(false);
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds

  const queryClient = useQueryClient();
  const { isConnected } = useWebSocket();

  // Mock data for demonstration (in real app, this would come from API)
  const mockStrategies: StrategyPerformanceMetrics[] = [
    {
      strategy_id: '1',
      name: 'Predator Alpha',
      category: 'Predatory',
      status: 'active',
      description: 'Advanced predatory trading strategy targeting market inefficiencies',
      created_at: '2024-01-15T00:00:00Z',
      updated_at: '2024-09-24T10:30:00Z',
      last_execution: '2024-09-24T10:25:00Z',

      // Core Performance
      total_return: 125000,
      total_return_percentage: 25.8,
      annual_return: 31.2,
      daily_pnl: 1250,
      weekly_pnl: 8750,
      monthly_pnl: 37500,

      // Risk Metrics
      sharpe_ratio: 1.85,
      sortino_ratio: 2.12,
      calmar_ratio: 1.45,
      max_drawdown: -45000,
      max_drawdown_percentage: -8.2,
      value_at_risk: -15000,
      expected_shortfall: -22000,
      volatility: 18.5,
      beta: 0.85,
      alpha: 5.2,

      // Trading Metrics
      total_trades: 324,
      winning_trades: 198,
      losing_trades: 126,
      win_rate: 61.1,
      profit_factor: 1.67,
      average_win: 2850,
      average_loss: -1720,
      largest_win: 15600,
      largest_loss: -8900,
      consecutive_wins: 8,
      consecutive_losses: 4,

      // Execution Metrics
      average_execution_time: 150,
      slippage: 0.02,
      commission_paid: 12500,
      net_profit: 112500,
      gross_profit: 125000,

      // Advanced Analytics
      information_ratio: 1.23,
      treynor_ratio: 0.185,
      jensen_alpha: 4.8,
      tracking_error: 8.5,
      upside_capture: 115.2,
      downside_capture: 78.3,

      // Time-based Performance
      daily_returns: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
        return: (Math.random() - 0.5) * 0.05,
        cumulative_return: i * 0.8 + Math.random() * 5,
        drawdown: Math.random() * -3,
        trades_count: Math.floor(Math.random() * 15),
        volume: Math.floor(Math.random() * 1000000),
      })),

      monthly_performance: Array.from({ length: 12 }, (_, i) => ({
        month: new Date(2024, i, 1).toLocaleDateString('en-US', { month: 'short' }),
        return: (Math.random() - 0.3) * 0.15,
        trades: Math.floor(Math.random() * 50) + 20,
        win_rate: 45 + Math.random() * 25,
        sharpe: 0.5 + Math.random() * 1.5,
      })),

      // Benchmarking
      benchmark_return: 12.5,
      excess_return: 13.3,
      benchmark_correlation: 0.65,

      // AI-Enhanced Metrics
      ai_confidence_score: 0.87,
      prediction_accuracy: 73.5,
      signal_strength: 0.82,
      market_regime_adaptation: 0.91,

      // Risk Management
      position_sizing_efficiency: 0.78,
      risk_adjusted_return: 1.42,
      tail_ratio: 0.85,
      pain_index: 0.15,
      sterling_ratio: 1.28,

      // Real-time Status
      is_live: true,
      current_positions: 8,
      unrealized_pnl: 2850,
      deployed_capital: 450000,
      available_capital: 50000,
      leverage_ratio: 1.2,

      // Alerts
      alerts: [
        {
          id: '1',
          type: 'info',
          message: 'Strategy performing above benchmark',
          timestamp: '2024-09-24T10:15:00Z',
        },
      ],
    },
    {
      strategy_id: '2',
      name: 'Vulture Approach',
      category: 'Predatory',
      status: 'active',
      description: 'Market stress exploitation strategy',
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-09-24T10:30:00Z',
      last_execution: '2024-09-24T10:20:00Z',

      // Core Performance
      total_return: 87500,
      total_return_percentage: 17.5,
      annual_return: 21.8,
      daily_pnl: 950,
      weekly_pnl: 6650,
      monthly_pnl: 28750,

      // Risk Metrics
      sharpe_ratio: 1.42,
      sortino_ratio: 1.68,
      calmar_ratio: 1.15,
      max_drawdown: -62500,
      max_drawdown_percentage: -11.8,
      value_at_risk: -18000,
      expected_shortfall: -28000,
      volatility: 22.3,
      beta: 1.15,
      alpha: 3.8,

      // Trading Metrics
      total_trades: 218,
      winning_trades: 128,
      losing_trades: 90,
      win_rate: 58.7,
      profit_factor: 1.52,
      average_win: 3200,
      average_loss: -2100,
      largest_win: 18900,
      largest_loss: -12400,
      consecutive_wins: 6,
      consecutive_losses: 5,

      // Execution Metrics
      average_execution_time: 180,
      slippage: 0.03,
      commission_paid: 8750,
      net_profit: 78750,
      gross_profit: 87500,

      // Advanced Analytics
      information_ratio: 0.98,
      treynor_ratio: 0.142,
      jensen_alpha: 3.2,
      tracking_error: 12.1,
      upside_capture: 108.5,
      downside_capture: 89.2,

      // Time-based Performance
      daily_returns: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
        return: (Math.random() - 0.5) * 0.04,
        cumulative_return: i * 0.6 + Math.random() * 4,
        drawdown: Math.random() * -4,
        trades_count: Math.floor(Math.random() * 12),
        volume: Math.floor(Math.random() * 800000),
      })),

      monthly_performance: Array.from({ length: 12 }, (_, i) => ({
        month: new Date(2024, i, 1).toLocaleDateString('en-US', { month: 'short' }),
        return: (Math.random() - 0.4) * 0.12,
        trades: Math.floor(Math.random() * 40) + 15,
        win_rate: 40 + Math.random() * 30,
        sharpe: 0.3 + Math.random() * 1.2,
      })),

      // Benchmarking
      benchmark_return: 12.5,
      excess_return: 5.0,
      benchmark_correlation: 0.58,

      // AI-Enhanced Metrics
      ai_confidence_score: 0.79,
      prediction_accuracy: 68.2,
      signal_strength: 0.76,
      market_regime_adaptation: 0.85,

      // Risk Management
      position_sizing_efficiency: 0.72,
      risk_adjusted_return: 1.18,
      tail_ratio: 0.78,
      pain_index: 0.22,
      sterling_ratio: 1.08,

      // Real-time Status
      is_live: true,
      current_positions: 5,
      unrealized_pnl: -1200,
      deployed_capital: 380000,
      available_capital: 120000,
      leverage_ratio: 0.9,

      // Alerts
      alerts: [
        {
          id: '2',
          type: 'warning',
          message: 'Drawdown approaching threshold',
          timestamp: '2024-09-24T09:45:00Z',
        },
      ],
    },
  ];

  // Query for strategy performance data
  const { data: strategiesData, isLoading, error, refetch } = useQuery({
    queryKey: ['strategy-performance', filters],
    queryFn: async () => {
      // In real app, this would call the API
      return mockStrategies;
    },
    refetchInterval: realTimeUpdates ? refreshInterval : false,
    staleTime: 5000,
  });

  // Filter strategies based on current filters
  const filteredStrategies = useMemo(() => {
    if (!strategiesData) return [];

    return strategiesData.filter(strategy => {
      if (filters.categories.length > 0 && !filters.categories.includes(strategy.category)) {
        return false;
      }
      if (filters.status.length > 0 && !filters.status.includes(strategy.status)) {
        return false;
      }
      if (strategy.total_return_percentage < filters.minReturn) {
        return false;
      }
      if (Math.abs(strategy.max_drawdown_percentage) > filters.maxDrawdown) {
        return false;
      }
      if (strategy.sharpe_ratio < filters.minSharpe) {
        return false;
      }
      if (strategy.win_rate < filters.minWinRate) {
        return false;
      }
      return true;
    });
  }, [strategiesData, filters]);

  // Handle strategy selection
  const handleStrategySelect = useCallback((strategyId: string) => {
    setSelectedStrategies(prev => {
      const isSelected = prev.includes(strategyId);
      const newSelection = isSelected
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId];

      onStrategySelect?.(strategyId);
      return newSelection;
    });
  }, [onStrategySelect]);

  // WebSocket real-time updates
  useEffect(() => {
    if (!realTimeUpdates || !isConnected) return;

    // In real app, set up WebSocket listeners
    // const handleStrategyUpdate = (data: any) => {
    //   queryClient.setQueryData(['strategy-performance', filters], (oldData: StrategyPerformanceMetrics[] | undefined) => {
    //     if (!oldData) return oldData;
    //
    //     return oldData.map(strategy =>
    //       strategy.strategy_id === data.strategy_id
    //         ? { ...strategy, ...data }
    //         : strategy
    //     );
    //   });
    // };
    // websocketService.on('strategy_performance_update', handleStrategyUpdate);

    return () => {
      // websocketService.off('strategy_performance_update', handleStrategyUpdate);
    };
  }, [realTimeUpdates, isConnected, queryClient, filters]);

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load strategy performance</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
        <button
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const selectedStrategyData = filteredStrategies.filter(s =>
    selectedStrategies.length === 0 || selectedStrategies.includes(s.strategy_id)
  );

  return (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
      {/* Header with controls */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <BarChart3 className="w-6 h-6 mr-2 text-blue-600" />
              Strategy Performance
            </h2>
            <p className="text-gray-600">
              Comprehensive analysis of {filteredStrategies.length} trading strategies
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {/* Real-time indicator */}
            {realTimeUpdates && (
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-xs text-gray-500">
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>
            )}

            {/* Refresh controls */}
            <div className="flex items-center space-x-2">
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="text-xs border rounded px-2 py-1"
                title="Auto-refresh interval"
              >
                <option value={5000}>5s</option>
                <option value={15000}>15s</option>
                <option value={30000}>30s</option>
                <option value={60000}>1m</option>
                <option value={0}>Manual</option>
              </select>
              <button
                onClick={() => refetch()}
                className="text-gray-400 hover:text-gray-600"
                title="Refresh data"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {/* View mode toggle */}
            <div className="flex border rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1 text-xs ${
                  viewMode === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
                }`}
                title="Grid view"
              >
                <PieChart className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1 text-xs ${
                  viewMode === 'table' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
                }`}
                title="Table view"
              >
                <BarChart2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('chart')}
                className={`px-3 py-1 text-xs ${
                  viewMode === 'chart' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
                }`}
                title="Chart view"
              >
                <LineChart className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Timeframe filter */}
          <select
            value={filters.timeframe}
            onChange={(e) => setFilters(prev => ({ ...prev, timeframe: e.target.value as 'day' | 'week' | 'month' | 'quarter' | 'year' | 'ytd' | 'all' }))}
            className="border rounded px-3 py-1 text-sm"
            title="Select timeframe"
          >
            <option value="day">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
            <option value="ytd">Year to Date</option>
            <option value="all">All Time</option>
          </select>

          {/* Status filter */}
          <select
            multiple
            value={filters.status}
            onChange={(e) => setFilters(prev => ({
              ...prev,
              status: Array.from(e.target.selectedOptions, option => option.value)
            }))}
            className="border rounded px-3 py-1 text-sm"
            title="Select strategy status"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="backtesting">Backtesting</option>
            <option value="paused">Paused</option>
          </select>

          {/* Quick filters */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Min Return:</label>
            <input
              type="number"
              value={filters.minReturn}
              onChange={(e) => setFilters(prev => ({ ...prev, minReturn: Number(e.target.value) }))}
              className="border rounded px-2 py-1 text-sm w-20"
              placeholder="%"
            />
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Max Drawdown:</label>
            <input
              type="number"
              value={filters.maxDrawdown}
              onChange={(e) => setFilters(prev => ({ ...prev, maxDrawdown: Number(e.target.value) }))}
              className="border rounded px-2 py-1 text-sm w-20"
              placeholder="%"
            />
          </div>

          {/* Advanced toggle */}
          <button
            onClick={() => setShowAdvancedMetrics(!showAdvancedMetrics)}
            className={`px-3 py-1 text-sm rounded ${
              showAdvancedMetrics ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            <Sliders className="w-4 h-4 inline mr-1" />
            Advanced
          </button>
        </div>
      </div>

      {/* Content based on view mode */}
      <div className="p-6">
        {viewMode === 'grid' && (
          <div className="space-y-8">
            {selectedStrategyData.length > 0 ? (
              selectedStrategyData.map((strategy) => (
                <div key={strategy.strategy_id} className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold text-gray-900">{strategy.name}</h3>
                      <span className="text-sm text-gray-500">({strategy.category})</span>
                      <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                        formatStrategyStatus(strategy.status).bgColor
                      } ${formatStrategyStatus(strategy.status).color}`}>
                        {formatStrategyStatus(strategy.status).text}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {strategy.alerts.length > 0 && (
                        <div className="flex items-center text-amber-600">
                          <AlertTriangle className="w-4 h-4 mr-1" />
                          <span className="text-xs">{strategy.alerts.length}</span>
                        </div>
                      )}
                      <button
                        onClick={() => setExpandedStrategy(
                          expandedStrategy === strategy.strategy_id ? null : strategy.strategy_id
                        )}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {expandedStrategy === strategy.strategy_id ?
                          <Minimize2 className="w-4 h-4" /> :
                          <Maximize2 className="w-4 h-4" />
                        }
                      </button>
                    </div>
                  </div>

                  <MetricsGrid
                    strategy={strategy}
                    showAdvanced={showAdvancedMetrics || expandedStrategy === strategy.strategy_id}
                  />

                  {expandedStrategy === strategy.strategy_id && (
                    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                      <PerformanceChart
                        data={[strategy]}
                        chartType={chartType}
                        timeframe={filters.timeframe}
                        showBenchmark={showBenchmark}
                      />

                      {/* Strategy alerts */}
                      {strategy.alerts.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-sm font-medium text-gray-900">Recent Alerts</h4>
                          {strategy.alerts.map((alert) => (
                            <div key={alert.id} className={`p-2 rounded text-sm ${
                              alert.type === 'error' ? 'bg-red-100 text-red-800' :
                              alert.type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                              alert.type === 'success' ? 'bg-green-100 text-green-800' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              <div className="flex items-center justify-between">
                                <span>{alert.message}</span>
                                <span className="text-xs opacity-75">
                                  {formatRelativeTime(alert.timestamp)}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                <BarChart3 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No strategies selected</h3>
                <p className="text-gray-500">Select strategies from the table view to see detailed performance</p>
              </div>
            )}
          </div>
        )}

        {viewMode === 'table' && showComparison && (
          <ComparisonTable
            strategies={filteredStrategies}
            onStrategySelect={handleStrategySelect}
            selectedStrategies={selectedStrategies}
          />
        )}

        {viewMode === 'chart' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Performance Comparison</h3>

              <div className="flex items-center space-x-3">
                <select
                  value={chartType}
                  onChange={(e) => setChartType(e.target.value as 'line' | 'bar' | 'area')}
                  className="border rounded px-3 py-1 text-sm"
                  title="Select chart type"
                >
                  <option value="line">Line Chart</option>
                  <option value="area">Area Chart</option>
                  <option value="bar">Bar Chart</option>
                </select>

                <label className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={showBenchmark}
                    onChange={(e) => setShowBenchmark(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span>Show Benchmark</span>
                </label>
              </div>
            </div>

            <PerformanceChart
              data={selectedStrategyData.length > 0 ? selectedStrategyData : filteredStrategies}
              chartType={chartType}
              timeframe={filters.timeframe}
              showBenchmark={showBenchmark}
            />
          </div>
        )}

        {/* Summary Statistics */}
        {!compactView && filteredStrategies.length > 0 && (
          <div className="mt-8 bg-gray-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Summary</h3>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {filteredStrategies.length}
                </div>
                <div className="text-sm text-gray-500">Active Strategies</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatPercentage(
                    filteredStrategies.reduce((sum, s) => sum + s.total_return_percentage, 0) /
                    filteredStrategies.length / 100
                  )}
                </div>
                <div className="text-sm text-gray-500">Avg Return</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {(filteredStrategies.reduce((sum, s) => sum + s.sharpe_ratio, 0) /
                    filteredStrategies.length).toFixed(2)}
                </div>
                <div className="text-sm text-gray-500">Avg Sharpe</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-amber-600">
                  {formatPercentage(
                    filteredStrategies.reduce((sum, s) => sum + s.win_rate, 0) /
                    filteredStrategies.length / 100
                  )}
                </div>
                <div className="text-sm text-gray-500">Avg Win Rate</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {formatPercentage(
                    Math.abs(filteredStrategies.reduce((sum, s) => sum + s.max_drawdown_percentage, 0)) /
                    filteredStrategies.length / 100
                  )}
                </div>
                <div className="text-sm text-gray-500">Avg Drawdown</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">
                  {formatCompactNumber(
                    filteredStrategies.reduce((sum, s) => sum + s.total_trades, 0)
                  )}
                </div>
                <div className="text-sm text-gray-500">Total Trades</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyPerformance;
