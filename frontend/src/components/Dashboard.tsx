import React, { useState, useEffect } from 'react';
import { Activity, BarChart3, Brain, Zap, AlertCircle, TrendingUp, TrendingDown, RefreshCw, Settings, Bell, Moon, Sun } from 'lucide-react';
import { useSystemStatus, usePortfolio, useActiveStrategies, useRecentTrades, useAIPredictions, useWebSocket } from '../hooks/useApi';
import {
  formatCurrency,
  formatPercentage,
  formatCompactNumber,
  formatRelativeTime,
  formatPnL,
  formatStrategyStatus,
  formatTradeSide,
  formatPredictionDirection,
  formatSystemStatus,
  formatTradingMode,
  formatMarketHours,
  formatConfidence,
  formatErrorMessage,
  getEmptyMessage,
} from '../utils/formatters';

// System Alerts Card Component
const SystemAlertsCard: React.FC = () => {
  const [alerts, setAlerts] = useState([
    {
      id: '1',
      level: 'warning' as const,
      message: 'Market volatility increased - Consider reducing position sizes',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      acknowledged: false
    },
    {
      id: '2',
      level: 'info' as const,
      message: 'New AI model version deployed - Enhanced prediction accuracy',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      acknowledged: false
    },
    {
      id: '3',
      level: 'error' as const,
      message: 'Connection to Dhan API unstable - Using cached data',
      timestamp: new Date(Date.now() - 900000).toISOString(),
      acknowledged: true
    }
  ]);

  const acknowledgeAlert = (id: string) => {
    setAlerts(prev => prev.map(alert =>
      alert.id === id ? { ...alert, acknowledged: true } : alert
    ));
  };

  const unacknowledgedAlerts = alerts.filter(alert => !alert.acknowledged);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">System Alerts</h3>
        <div className="flex items-center space-x-2">
          {unacknowledgedAlerts.length > 0 && (
            <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {unacknowledgedAlerts.length}
            </span>
          )}
          <AlertCircle className="w-5 h-5 text-gray-400" />
        </div>
      </div>

      {alerts.length > 0 ? (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {alerts.map((alert) => {
            const levelColors = {
              error: 'border-red-500 bg-red-50',
              warning: 'border-yellow-500 bg-yellow-50',
              info: 'border-blue-500 bg-blue-50'
            };

            const levelIcons = {
              error: '❌',
              warning: '⚠️',
              info: 'ℹ️'
            };

            return (
              <div key={alert.id} className={`p-3 rounded-lg border-l-4 ${levelColors[alert.level]} ${alert.acknowledged ? 'opacity-60' : ''}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-lg">{levelIcons[alert.level]}</span>
                      <span className="text-sm font-medium text-gray-900 capitalize">{alert.level}</span>
                    </div>
                    <p className="text-sm text-gray-700">{alert.message}</p>
                    <p className="text-xs text-gray-500 mt-1">{formatRelativeTime(alert.timestamp)}</p>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.id)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium ml-2"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8">
          <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No system alerts</p>
        </div>
      )}
    </div>
  );
};
const MarketDataCard: React.FC = () => {
  const [marketData, setMarketData] = useState([
    { symbol: 'NIFTY50', price: 22134.75, change: 156.25, change_percentage: 0.71, volume: 245678900 },
    { symbol: 'BANKNIFTY', price: 48256.30, change: -234.80, change_percentage: -0.48, volume: 123456789 },
    { symbol: 'RELIANCE', price: 2456.80, change: 23.45, change_percentage: 0.96, volume: 3456789 },
    { symbol: 'TCS', price: 3245.60, change: -12.30, change_percentage: -0.38, volume: 2345678 },
  ]);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMarketData(prev => prev.map(item => ({
        ...item,
        price: item.price + (Math.random() - 0.5) * 10,
        change: item.change + (Math.random() - 0.5) * 5,
        change_percentage: item.change_percentage + (Math.random() - 0.5) * 0.1,
      })));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Market Overview</h3>
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-4 h-4 text-gray-400 animate-spin" />
          <span className="text-xs text-gray-500">Live</span>
        </div>
      </div>

      <div className="space-y-3">
        {marketData.map((item) => (
          <div key={item.symbol} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex-1">
              <p className="font-medium text-gray-900">{item.symbol}</p>
              <p className="text-sm text-gray-500">{formatCompactNumber(item.volume)} vol</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{formatCurrency(item.price)}</p>
              <p className={`text-xs flex items-center ${item.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {item.change >= 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
                {formatCurrency(Math.abs(item.change))} ({formatPercentage(item.change_percentage / 100)})
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
const SystemStatusCard: React.FC = () => {
  const { data: systemStatus, isLoading, error } = useSystemStatus();
  const { isConnected } = useWebSocket();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load system status</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  if (!systemStatus) return null;

  const statusInfo = formatSystemStatus(systemStatus.status);
  const modeInfo = formatTradingMode(systemStatus.trading_mode);
  const marketInfo = formatMarketHours(systemStatus.market_hours);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-xs text-gray-500">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="text-center">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${statusInfo.bgColor} ${statusInfo.color}`}>
            {statusInfo.icon} {statusInfo.text}
          </div>
          <p className="text-xs text-gray-500 mt-1">System Health</p>
        </div>

        <div className="text-center">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${modeInfo.bgColor} ${modeInfo.color}`}>
            {modeInfo.text}
          </div>
          <p className="text-xs text-gray-500 mt-1">Trading Mode</p>
        </div>

        <div className="text-center">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${marketInfo.bgColor} ${marketInfo.color}`}>
            {marketInfo.text}
          </div>
          <p className="text-xs text-gray-500 mt-1">Market Hours</p>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-500">
        Last updated: {formatRelativeTime(systemStatus.timestamp)}
      </div>
    </div>
  );
};

// Portfolio Summary Card Component
const PortfolioSummaryCard: React.FC = () => {
  const { data: portfolio, isLoading, error } = usePortfolio();
  const [showDetails, setShowDetails] = useState(false);

  type DisplaySummary = {
    totalValue: number;
    totalPnL: number;
    totalPnLPercent: number;
    dayPnL: number;
    dayPnLPercent: number;
    positionsCount: number;
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center text-red-600">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span className="text-sm">Failed to load portfolio</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  if (!portfolio) return null;

  const computePercentage = (value: number, base: number) => {
    if (!base || Math.abs(base) < 1e-6) {
      return 0;
    }
    return (value / base) * 100;
  };

  const mapAggregateSummary = (summary: typeof portfolio.summary): DisplaySummary => ({
    totalValue: summary.total_market_value,
    totalPnL: summary.total_pnl,
    totalPnLPercent: computePercentage(summary.total_pnl, summary.total_margin_used),
    dayPnL: summary.daily_pnl,
    dayPnLPercent: computePercentage(summary.daily_pnl, summary.total_margin_used),
    positionsCount: summary.total_positions,
  });

  const aggregatePositions = (positions: typeof portfolio.positions): DisplaySummary => {
    const aggregates = positions.reduce(
      (acc, position) => {
        const notional = Math.abs(position.quantity * position.average_price);
        const margin = position.margin_used ?? notional;

        return {
          totalValue: acc.totalValue + (position.market_value ?? notional),
          totalPnL: acc.totalPnL + (position.total_pnl ?? position.unrealized_pnl ?? 0),
          dayPnL: acc.dayPnL + (position.daily_pnl ?? 0),
          totalMargin: acc.totalMargin + (margin > 0 ? margin : notional),
        };
      },
      { totalValue: 0, totalPnL: 0, dayPnL: 0, totalMargin: 0 }
    );

    const { totalValue, totalPnL, dayPnL, totalMargin } = aggregates;
    return {
      totalValue,
      totalPnL,
      totalPnLPercent: totalMargin > 0 ? (totalPnL / totalMargin) * 100 : 0,
      dayPnL,
      dayPnLPercent: totalMargin > 0 ? (dayPnL / totalMargin) * 100 : 0,
      positionsCount: positions.length,
    };
  };

  const overallSummary = mapAggregateSummary(portfolio.summary);
  const paperPositions = portfolio.positions.filter((position) => position.is_paper_position);
  const livePositions = portfolio.positions.filter((position) => !position.is_paper_position);
  const paperSummary = aggregatePositions(paperPositions);
  const liveSummary = aggregatePositions(livePositions);

  const accountSummaries: Array<{ label: string; summary: DisplaySummary }> = [
    { label: 'Paper Trading', summary: paperSummary },
    { label: 'Live Trading', summary: liveSummary },
  ];

  const pnlInfo = formatPnL(overallSummary.totalPnL, overallSummary.totalPnLPercent);
  const dayPnLInfo = formatPnL(overallSummary.dayPnL, overallSummary.dayPnLPercent);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Portfolio Summary</h3>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(overallSummary.totalValue)}
          </p>
          <p className="text-xs text-gray-500">Total Value</p>
        </div>

        <div>
          <p className={`text-2xl font-bold ${pnlInfo.color}`}>
            {pnlInfo.value}
          </p>
          <p className={`text-xs ${pnlInfo.color}`}>Total P&L{pnlInfo.percentage}</p>
        </div>

        <div>
          <p className={`text-2xl font-bold ${dayPnLInfo.color}`}>
            {dayPnLInfo.value}
          </p>
          <p className={`text-xs ${dayPnLInfo.color}`}>Day P&L{dayPnLInfo.percentage}</p>
        </div>

        <div>
          <p className="text-2xl font-bold text-gray-900">
            {overallSummary.positionsCount}
          </p>
          <p className="text-xs text-gray-500">Positions</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {accountSummaries.map(({ label, summary }) => {
          const accountPnL = formatPnL(summary.totalPnL, summary.totalPnLPercent);
          const accountDayPnL = formatPnL(summary.dayPnL, summary.dayPnLPercent);

          return (
            <div key={label} className="p-4 rounded-lg bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-gray-600">{label}</p>
                <span className="text-xs text-gray-500">{summary.positionsCount} positions</span>
              </div>
              <p className="text-xl font-semibold text-gray-900">{formatCurrency(summary.totalValue)}</p>
              <div className="flex items-center justify-between text-xs mt-2">
                <span className={`${accountPnL.color} font-medium`}>
                  Total {accountPnL.value}
                  {accountPnL.percentage}
                </span>
                <span className={`${accountDayPnL.color} font-medium`}>
                  Day {accountDayPnL.value}
                  {accountDayPnL.percentage}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Portfolio Positions Details */}
      {showDetails && portfolio.positions.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Position Details</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {portfolio.positions.map((position) => {
              const notional = Math.abs(position.quantity * position.average_price);
              const margin = position.margin_used ?? notional;
              const pnlPercent = margin > 0 ? (position.unrealized_pnl / margin) * 100 : 0;
              const positionPnL = formatPnL(position.unrealized_pnl, pnlPercent);
              const accountBadgeStyles = position.is_paper_position
                ? 'bg-blue-100 text-blue-700'
                : 'bg-red-100 text-red-700';

              return (
                <div key={position.portfolio_id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{position.symbol}</p>
                    <p className="text-xs text-gray-500">
                      {formatCompactNumber(Math.abs(position.quantity))} @ {formatCurrency(position.average_price)}
                      <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${accountBadgeStyles}`}>
                        {position.is_paper_position ? 'Paper' : 'Live'}
                      </span>
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-gray-900">{formatCurrency(position.market_value)}</p>
                    <p className={`text-xs ${positionPnL.color}`}>
                      {positionPnL.value}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        Last updated: {formatRelativeTime(portfolio.last_updated)}
      </div>
    </div>
  );
};

// Active Strategies Card Component
const ActiveStrategiesCard: React.FC = () => {
  const { data: strategies, isLoading, error } = useActiveStrategies();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
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
          <span className="text-sm">Failed to load strategies</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Active Strategies</h3>
        <BarChart3 className="w-5 h-5 text-gray-400" />
      </div>

      {strategies && strategies.length > 0 ? (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {strategies.slice(0, 5).map((strategy) => {
            const statusInfo = formatStrategyStatus(strategy.status);
            return (
              <div key={strategy.strategy_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{strategy.name}</p>
                  <p className="text-sm text-gray-500">{strategy.description}</p>
                </div>
                <div className="flex items-center space-x-2">
                  {strategy.performance_metrics && (
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        {formatPercentage(strategy.performance_metrics.total_return / 100)}
                      </p>
                      <p className="text-xs text-gray-500">Return</p>
                    </div>
                  )}
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${statusInfo.bgColor} ${statusInfo.color}`}>
                    {statusInfo.text}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8">
          <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{getEmptyMessage('strategies')}</p>
        </div>
      )}
    </div>
  );
};

// Recent Trades Card Component
const RecentTradesCard: React.FC = () => {
  const { data: trades, isLoading, error } = useRecentTrades();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
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
          <span className="text-sm">Failed to load trades</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{formatErrorMessage(error)}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Recent Trades</h3>
        <Activity className="w-5 h-5 text-gray-400" />
      </div>

      {trades && trades.trades.length > 0 ? (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {trades.trades.slice(0, 5).map((trade) => {
            const sideInfo = formatTradeSide(trade.side);
            return (
              <div key={trade.trade_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{trade.symbol}</p>
                  <p className="text-sm text-gray-500">{formatRelativeTime(trade.timestamp)}</p>
                </div>
                <div className="flex items-center space-x-3">
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${sideInfo.bgColor} ${sideInfo.color}`}>
                    {sideInfo.text}
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      {formatCompactNumber(trade.quantity)}
                    </p>
                    <p className="text-xs text-gray-500">Qty</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      {formatCurrency(trade.price)}
                    </p>
                    <p className="text-xs text-gray-500">Price</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-8">
          <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{getEmptyMessage('trades')}</p>
        </div>
      )}
    </div>
  );
};

// AI Predictions Card Component
const AIPredictionsCard: React.FC = () => {
  const { data: predictions, isLoading, error } = useAIPredictions();
  const [confidenceFilter, setConfidenceFilter] = useState(0.7);
  const [showAll, setShowAll] = useState(false);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-12 bg-gray-200 rounded"></div>
            <div className="h-12 bg-gray-200 rounded"></div>
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

  const filteredPredictions = predictions?.predictions.filter(p => p.confidence_score >= confidenceFilter) || [];
  const displayPredictions = showAll ? filteredPredictions : filteredPredictions.slice(0, 5);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">AI Predictions</h3>
        <Brain className="w-5 h-5 text-gray-400" />
      </div>

      {/* Confidence Filter */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Minimum Confidence: {Math.round(confidenceFilter * 100)}%
        </label>
        <input
          type="range"
          min="0.5"
          max="0.95"
          step="0.05"
          value={confidenceFilter}
          onChange={(e) => setConfidenceFilter(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          aria-label="Minimum confidence threshold"
          title="Adjust minimum confidence threshold for AI predictions"
        />
      </div>

      {displayPredictions.length > 0 ? (
        <div className="space-y-3">
          {displayPredictions.map((prediction) => {
            const directionInfo = formatPredictionDirection(prediction.predicted_direction);
            const confidenceInfo = formatConfidence(prediction.confidence_score);
            return (
              <div key={prediction.prediction_id} className="p-3 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900">{prediction.symbol}</span>
                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${directionInfo.bgColor} ${directionInfo.color}`}>
                      {directionInfo.icon} {directionInfo.text}
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${confidenceInfo.color}`}>
                    {confidenceInfo.text}
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

          {filteredPredictions.length > 5 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="w-full text-center text-sm text-blue-600 hover:text-blue-800 font-medium py-2"
            >
              {showAll ? 'Show Less' : `Show ${filteredPredictions.length - 5} More`}
            </button>
          )}
        </div>
      ) : (
        <div className="text-center py-8">
          <Brain className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">{getEmptyMessage('predictions')}</p>
          <p className="text-sm text-gray-400 mt-1">
            Try lowering the confidence threshold
          </p>
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
const Dashboard: React.FC = () => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [notifications, setNotifications] = useState<string[]>([]);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);

  const { isConnected } = useWebSocket();

  // Add notification for WebSocket events
  useEffect(() => {
    if (isConnected) {
      setNotifications(prev => [...prev.slice(-4), 'Connected to real-time data stream']);
    } else {
      setNotifications(prev => [...prev.slice(-4), 'Disconnected from real-time data stream']);
    }
  }, [isConnected]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case 'd':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            setIsDarkMode(!isDarkMode);
          }
          break;
        case '?':
          event.preventDefault();
          setShowKeyboardShortcuts(!showKeyboardShortcuts);
          break;
        case 'r':
          if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            window.location.reload();
          }
          break;
        case 'escape':
          setShowKeyboardShortcuts(false);
          break;
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [isDarkMode, showKeyboardShortcuts]);

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
    // In a real app, you'd save this to localStorage and apply dark mode classes
  };

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-50'}`}>
      {/* Keyboard Shortcuts Modal */}
      {showKeyboardShortcuts && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowKeyboardShortcuts(false)}>
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">Keyboard Shortcuts</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Toggle Dark Mode</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+D</kbd>
              </div>
              <div className="flex justify-between">
                <span>Show Shortcuts</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded">?</kbd>
              </div>
              <div className="flex justify-between">
                <span>Refresh Page</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded">Ctrl+R</kbd>
              </div>
              <div className="flex justify-between">
                <span>Close Modal</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded">Esc</kbd>
              </div>
            </div>
            <button
              onClick={() => setShowKeyboardShortcuts(false)}
              className="mt-4 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white'} shadow-sm border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">NIRAJ Trading Dashboard</h1>
              <p className="text-gray-600">Advanced Self-Learning Algorithmic AI Personal Trading System</p>
            </div>
            <div className="flex items-center space-x-4">
              {/* Help Button */}
              <button
                onClick={() => setShowKeyboardShortcuts(true)}
                className="text-gray-400 hover:text-gray-600 text-sm"
                title="Keyboard shortcuts (?)"
              >
                ?
              </button>

              {/* Notifications */}
              <div className="relative">
                <Bell className="w-5 h-5 text-gray-400 cursor-pointer hover:text-gray-600" />
                {notifications.length > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {notifications.length}
                  </span>
                )}
              </div>

              {/* Dark Mode Toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                title="Toggle dark mode (Ctrl+D)"
              >
                {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>

              {/* Settings */}
              <Settings className="w-5 h-5 text-gray-400 cursor-pointer hover:text-gray-600" />

              <div className="flex items-center space-x-2">
                <Zap className="w-5 h-5 text-blue-500" />
                <span className="text-sm font-medium text-gray-700">AI-Powered</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Row - System Status and Portfolio Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <SystemStatusCard />
          <PortfolioSummaryCard />
        </div>

        {/* Second Row - Market Data and Active Strategies */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <MarketDataCard />
          <ActiveStrategiesCard />
        </div>

        {/* Third Row - Recent Trades and AI Predictions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <RecentTradesCard />
          <AIPredictionsCard />
        </div>

        {/* Fourth Row - System Alerts */}
        <div className="grid grid-cols-1 gap-6 mb-8">
          <SystemAlertsCard />
        </div>

        {/* Notifications Panel */}
        {notifications.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <Bell className="w-5 h-5 text-blue-500 mr-2" />
                <span className="text-sm font-medium text-blue-800">Recent Notifications</span>
              </div>
              <button
                onClick={() => setNotifications([])}
                className="text-blue-600 hover:text-blue-800 text-sm"
              >
                Clear
              </button>
            </div>
            <div className="mt-2 space-y-1">
              {notifications.slice(-3).map((notification, index) => (
                <p key={index} className="text-sm text-blue-700">{notification}</p>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
