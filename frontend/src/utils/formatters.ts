// Utility functions for data formatting and display

// Currency formatting
export const formatCurrency = (amount: number, currency = 'INR'): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

// Percentage formatting
export const formatPercentage = (value: number, decimals = 2): string => {
  const formatted = (value * 100).toFixed(decimals);
  const numValue = parseFloat(formatted);
  return `${numValue >= 0 ? '+' : ''}${formatted}%`;
};

// Number formatting with Indian numbering system
export const formatNumber = (num: number, decimals = 2): string => {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
};

// Compact number formatting (K, M, B, T)
export const formatCompactNumber = (num: number): string => {
  return new Intl.NumberFormat('en-IN', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(num);
};

// Date and time formatting
export const formatDate = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

export const formatTime = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export const formatDateTime = (date: string | Date): string => {
  const d = new Date(date);
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Relative time formatting
export const formatRelativeTime = (date: string | Date): string => {
  const now = new Date();
  const d = new Date(date);
  const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

  return formatDate(d);
};

// Trading specific formatting
export const formatPriceChange = (change: number, changePercent: number): string => {
  const sign = change >= 0 ? '+' : '';
  return `${sign}${formatCurrency(change)} (${formatPercentage(changePercent / 100)})`;
};

export const formatVolume = (volume: number): string => {
  if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
  if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
  if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
  return formatNumber(volume, 0);
};

// Confidence score formatting
export const formatConfidence = (confidence: number): { percentage: number; color: string; text: string } => {
  const percentage = Math.round(confidence * 100);
  let color = 'text-gray-500';
  if (percentage >= 80) color = 'text-green-600';
  else if (percentage >= 60) color = 'text-yellow-600';
  else if (percentage >= 40) color = 'text-orange-600';
  else color = 'text-red-600';

  return { percentage, color, text: `${percentage}%` };
};

// P&L formatting with color coding
export const formatPnL = (pnl: number, percentage?: number): { value: string; percentage: string; color: string } => {
  const isPositive = pnl >= 0;
  const color = isPositive ? 'text-green-600' : 'text-red-600';
  const sign = isPositive ? '+' : '';

  const value = `${sign}${formatCurrency(pnl)}`;
  const percentageText = percentage !== undefined ? ` (${formatPercentage(percentage / 100)})` : '';

  return {
    value,
    percentage: percentageText,
    color,
  };
};

// Strategy status formatting
export const formatStrategyStatus = (status: string): { text: string; color: string; bgColor: string } => {
  switch (status.toLowerCase()) {
    case 'active':
      return { text: 'Active', color: 'text-green-700', bgColor: 'bg-green-100' };
    case 'inactive':
      return { text: 'Inactive', color: 'text-gray-700', bgColor: 'bg-gray-100' };
    case 'backtesting':
      return { text: 'Backtesting', color: 'text-blue-700', bgColor: 'bg-blue-100' };
    default:
      return { text: status, color: 'text-gray-700', bgColor: 'bg-gray-100' };
  }
};

// Trade side formatting
export const formatTradeSide = (side: string): { text: string; color: string; bgColor: string } => {
  switch (side.toLowerCase()) {
    case 'buy':
      return { text: 'Buy', color: 'text-green-700', bgColor: 'bg-green-100' };
    case 'sell':
      return { text: 'Sell', color: 'text-red-700', bgColor: 'bg-red-100' };
    default:
      return { text: side, color: 'text-gray-700', bgColor: 'bg-gray-100' };
  }
};

// Trade status formatting
export const formatTradeStatus = (status: string): { text: string; color: string; bgColor: string } => {
  switch (status.toLowerCase()) {
    case 'executed':
      return { text: 'Executed', color: 'text-green-700', bgColor: 'bg-green-100' };
    case 'pending':
      return { text: 'Pending', color: 'text-yellow-700', bgColor: 'bg-yellow-100' };
    case 'cancelled':
      return { text: 'Cancelled', color: 'text-red-700', bgColor: 'bg-red-100' };
    default:
      return { text: status, color: 'text-gray-700', bgColor: 'bg-gray-100' };
  }
};

// AI prediction direction formatting
export const formatPredictionDirection = (direction: string): { text: string; color: string; bgColor: string; icon: string } => {
  switch (direction.toUpperCase()) {
    case 'UP':
      return { text: 'Bullish', color: 'text-green-700', bgColor: 'bg-green-100', icon: '↗️' };
    case 'DOWN':
      return { text: 'Bearish', color: 'text-red-700', bgColor: 'bg-red-100', icon: '↘️' };
    case 'SIDEWAYS':
      return { text: 'Neutral', color: 'text-yellow-700', bgColor: 'bg-yellow-100', icon: '➡️' };
    default:
      return { text: direction, color: 'text-gray-700', bgColor: 'bg-gray-100', icon: '❓' };
  }
};

// System status formatting
export const formatSystemStatus = (status: string): { text: string; color: string; bgColor: string; icon: string } => {
  switch (status.toLowerCase()) {
    case 'healthy':
      return { text: 'Healthy', color: 'text-green-700', bgColor: 'bg-green-100', icon: '✅' };
    case 'degraded':
      return { text: 'Degraded', color: 'text-yellow-700', bgColor: 'bg-yellow-100', icon: '⚠️' };
    case 'down':
      return { text: 'Down', color: 'text-red-700', bgColor: 'bg-red-100', icon: '❌' };
    default:
      return { text: status, color: 'text-gray-700', bgColor: 'bg-gray-100', icon: '❓' };
  }
};

// Trading mode formatting
export const formatTradingMode = (mode: string): { text: string; color: string; bgColor: string } => {
  switch (mode.toLowerCase()) {
    case 'live':
      return { text: 'Live Trading', color: 'text-red-700', bgColor: 'bg-red-100' };
    case 'paper':
      return { text: 'Paper Trading', color: 'text-blue-700', bgColor: 'bg-blue-100' };
    default:
      return { text: mode, color: 'text-gray-700', bgColor: 'bg-gray-100' };
  }
};

// Market hours formatting
export const formatMarketHours = (isOpen: boolean): { text: string; color: string; bgColor: string } => {
  if (isOpen) {
    return { text: 'Open', color: 'text-green-700', bgColor: 'bg-green-100' };
  } else {
    return { text: 'Closed', color: 'text-red-700', bgColor: 'bg-red-100' };
  }
};

// Error message formatting
export const formatErrorMessage = (error: unknown): string => {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    const errorObj = error as Record<string, unknown>;
    if (errorObj.message && typeof errorObj.message === 'string') return errorObj.message;

    // Handle Axios-style errors
    const response = errorObj.response as Record<string, unknown> | undefined;
    if (response?.data && typeof response.data === 'object') {
      const data = response.data as Record<string, unknown>;
      if (data.message && typeof data.message === 'string') return data.message;
      if (data.error && typeof data.error === 'string') return data.error;
    }
  }
  return 'An unexpected error occurred';
};

// Loading state helpers
export const getLoadingMessage = (context: string): string => {
  const messages = {
    portfolio: 'Loading portfolio data...',
    strategies: 'Loading trading strategies...',
    trades: 'Loading recent trades...',
    predictions: 'Loading AI predictions...',
    system: 'Loading system status...',
    default: 'Loading...',
  };
  return messages[context as keyof typeof messages] || messages.default;
};

// Empty state helpers
export const getEmptyMessage = (context: string): string => {
  const messages = {
    portfolio: 'No positions in your portfolio',
    strategies: 'No trading strategies configured',
    trades: 'No recent trades',
    predictions: 'No AI predictions available',
    default: 'No data available',
  };
  return messages[context as keyof typeof messages] || messages.default;
};
