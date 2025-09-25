import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Bell,
  BellOff,
  ChevronDown,
  ChevronUp,
  Loader2,
  Maximize2,
  Minimize2,
  Minus,
  Plus,
  RefreshCw,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../hooks/useApi';
import {
  formatCurrency,
  formatPercentage,
  formatCompactNumber,
  formatRelativeTime,
  formatDateTime,
  formatPnL,
  formatTradeSide,
  formatTradeStatus,
} from '../utils/formatters';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// Types for trading interface
interface OrderType {
  id: string;
  name: string;
  description: string;
  requiresPrice: boolean;
}

interface OrderFormData {
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: string;
  quantity: number;
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
  trailingStopDistance?: number; // For trailing stops
  ocoTargetPrice?: number; // For OCO orders
  ocoStopPrice?: number; // For OCO orders
  icebergVisibleQuantity?: number; // For iceberg orders
  timeInForce: string; // DAY, GTC, IOC, FOK
  strategyId?: string;
}

interface MarketData {
  symbol: string;
  price: number;
  change: number;
  change_percentage: number;
  volume: number;
  bid: number;
  ask: number;
  high: number;
  low: number;
  open: number;
  timestamp: string;
}

interface Position {
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  marketValue: number;
  unrealizedPnL: number;
  unrealizedPnLPercentage: number;
  realizedPnL: number;
  lastUpdated: string;
}

interface ActiveOrder {
  orderId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  orderType: string;
  quantity: number;
  price?: number;
  status: 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELLED';
  timestamp: string;
  strategyId?: string;
}

interface Trade {
  tradeId: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  timestamp: string;
  pnl?: number;
  strategyId?: string;
  status: 'EXECUTED' | 'PENDING' | 'CANCELLED';
}

interface TechnicalIndicators {
  rsi: number;
  macd: {
    value: number;
    signal: number;
    histogram: number;
  };
  bollingerBands: {
    upper: number;
    middle: number;
    lower: number;
  };
  movingAverages: {
    sma20: number;
    sma50: number;
    ema12: number;
    ema26: number;
  };
  stochastic: {
    k: number;
    d: number;
  };
}

interface NotificationItem {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

interface PriceData {
  timestamp: string;
  price: number;
  volume: number;
}

// Order types configuration
const ORDER_TYPES: OrderType[] = [
  { id: 'MARKET', name: 'Market', description: 'Execute immediately at best available price', requiresPrice: false },
  { id: 'LIMIT', name: 'Limit', description: 'Execute only at specified price or better', requiresPrice: true },
  { id: 'STOP', name: 'Stop', description: 'Convert to market order when stop price is reached', requiresPrice: true },
  { id: 'STOP_LIMIT', name: 'Stop Limit', description: 'Convert to limit order when stop price is reached', requiresPrice: true },
  { id: 'TRAILING_STOP', name: 'Trailing Stop', description: 'Dynamic stop loss that trails price movement', requiresPrice: false },
  { id: 'OCO', name: 'OCO (One Cancels Other)', description: 'Place two orders where filling one cancels the other', requiresPrice: true },
  { id: 'BRACKET', name: 'Bracket Order', description: 'Entry order with attached stop loss and take profit', requiresPrice: true },
  { id: 'ICEBERG', name: 'Iceberg', description: 'Large order executed in smaller visible quantities', requiresPrice: true },
];

// Time-in-Force options
const TIME_IN_FORCE_OPTIONS = [
  { id: 'DAY', name: 'Day', description: 'Valid for the trading day' },
  { id: 'GTC', name: 'GTC', description: 'Good Till Cancelled' },
  { id: 'IOC', name: 'IOC', description: 'Immediate or Cancel' },
  { id: 'FOK', name: 'FOK', description: 'Fill or Kill' },
];

// Main Trading Interface Component
const TradingInterface: React.FC = () => {
  // State management
  const [selectedSymbol, setSelectedSymbol] = useState<string>('NIFTY50');
  const [orderForm, setOrderForm] = useState<OrderFormData>({
    symbol: 'NIFTY50',
    side: 'BUY',
    orderType: 'MARKET',
    quantity: 1,
    timeInForce: 'DAY',
  });
  const [isOrderFormVisible, setIsOrderFormVisible] = useState(true);
  const [isPortfolioVisible, setIsPortfolioVisible] = useState(true);
  const [isMarketDataVisible, setIsMarketDataVisible] = useState(true);
  const [isIndicatorsVisible, setIsIndicatorsVisible] = useState(true);
  const [isOrdersVisible, setIsOrdersVisible] = useState(true);
  const [isTradesVisible, setIsTradesVisible] = useState(true);
  const [viewMode, setViewMode] = useState<'compact' | 'detailed'>('detailed');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  // const [riskManagement, setRiskManagement] = useState({ // Future feature
  const [riskManagement] = useState({
    maxPositionSize: 100000,
    maxDailyLoss: 50000,
    maxSingleTrade: 25000,
    riskPerTrade: 2, // percentage
  });

  // WebSocket connection
  const { isConnected } = useWebSocket();
  const queryClient = useQueryClient();

  // Market data query
  const { data: marketData, isLoading: marketLoading, error: marketError } = useQuery({
    queryKey: ['market-data', selectedSymbol],
    queryFn: async () => {
      // This would be replaced with actual API call
      return {
        symbol: selectedSymbol,
        price: 22134.75 + Math.random() * 100 - 50,
        change: Math.random() * 200 - 100,
        change_percentage: Math.random() * 2 - 1,
        volume: Math.floor(Math.random() * 1000000) + 500000,
        bid: 22130.00,
        ask: 22140.00,
        high: 22200.00,
        low: 22000.00,
        open: 22100.00,
        timestamp: new Date().toISOString(),
      } as MarketData;
    },
    refetchInterval: autoRefresh ? 2000 : false,
  });

  // Portfolio query
  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: async () => {
      // Mock portfolio data
      return [
        {
          symbol: 'NIFTY50',
          quantity: 25,
          averagePrice: 21800.50,
          currentPrice: marketData?.price || 22134.75,
          marketValue: (marketData?.price || 22134.75) * 25,
          unrealizedPnL: ((marketData?.price || 22134.75) - 21800.50) * 25,
          unrealizedPnLPercentage: (((marketData?.price || 22134.75) - 21800.50) / 21800.50) * 100,
          realizedPnL: 1250.75,
          lastUpdated: new Date().toISOString(),
        },
        {
          symbol: 'BANKNIFTY',
          quantity: -15,
          averagePrice: 48500.25,
          currentPrice: 48256.30,
          marketValue: 48256.30 * 15,
          unrealizedPnL: (48256.30 - 48500.25) * 15,
          unrealizedPnLPercentage: ((48256.30 - 48500.25) / 48500.25) * 100,
          realizedPnL: -890.50,
          lastUpdated: new Date().toISOString(),
        },
      ] as Position[];
    },
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Active orders query
  const { data: activeOrders, isLoading: ordersLoading } = useQuery({
    queryKey: ['active-orders'],
    queryFn: async () => {
      // Mock active orders
      return [
        {
          orderId: 'ORD001',
          symbol: 'NIFTY50',
          side: 'BUY' as const,
          orderType: 'LIMIT',
          quantity: 10,
          price: 22000.00,
          status: 'PENDING' as const,
          timestamp: new Date(Date.now() - 300000).toISOString(),
          strategyId: 'strat001',
        },
        {
          orderId: 'ORD002',
          symbol: 'BANKNIFTY',
          side: 'SELL' as const,
          orderType: 'STOP',
          quantity: 5,
          price: 49000.00,
          status: 'PENDING' as const,
          timestamp: new Date(Date.now() - 600000).toISOString(),
        },
      ] as ActiveOrder[];
    },
    refetchInterval: autoRefresh ? 3000 : false,
  });

  // Recent trades query
  const { data: recentTrades, isLoading: tradesLoading } = useQuery({
    queryKey: ['recent-trades'],
    queryFn: async () => {
      // Mock recent trades
      return [
        {
          tradeId: 'TRD001',
          symbol: 'NIFTY50',
          side: 'BUY' as const,
          quantity: 25,
          price: 21800.50,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          pnl: 837.50,
          strategyId: 'strat001',
          status: 'EXECUTED' as const,
        },
        {
          tradeId: 'TRD002',
          symbol: 'BANKNIFTY',
          side: 'SELL' as const,
          quantity: 15,
          price: 48500.25,
          timestamp: new Date(Date.now() - 7200000).toISOString(),
          pnl: -890.50,
          status: 'EXECUTED' as const,
        },
      ] as Trade[];
    },
    refetchInterval: autoRefresh ? 10000 : false,
  });

  // Technical indicators query
  const { data: technicalIndicators, isLoading: indicatorsLoading } = useQuery({
    queryKey: ['technical-indicators', selectedSymbol],
    queryFn: async () => {
      // Mock technical indicators calculation
      const basePrice = marketData?.price || 22134.75;
      const rsi = 45 + Math.random() * 40; // 45-85 range
      const macdValue = Math.random() * 200 - 100;
      const macdSignal = macdValue + (Math.random() * 50 - 25);
      const macdHistogram = macdValue - macdSignal;

      return {
        rsi: Math.round(rsi * 100) / 100,
        macd: {
          value: Math.round(macdValue * 100) / 100,
          signal: Math.round(macdSignal * 100) / 100,
          histogram: Math.round(macdHistogram * 100) / 100,
        },
        bollingerBands: {
          upper: basePrice * (1 + Math.random() * 0.05),
          middle: basePrice,
          lower: basePrice * (1 - Math.random() * 0.05),
        },
        movingAverages: {
          sma20: basePrice * (0.95 + Math.random() * 0.1),
          sma50: basePrice * (0.9 + Math.random() * 0.2),
          ema12: basePrice * (0.92 + Math.random() * 0.16),
          ema26: basePrice * (0.88 + Math.random() * 0.24),
        },
        stochastic: {
          k: 20 + Math.random() * 60,
          d: 25 + Math.random() * 50,
        },
      } as TechnicalIndicators;
    },
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Price history query for chart
  const { data: priceHistory, isLoading: priceHistoryLoading } = useQuery({
    queryKey: ['price-history', selectedSymbol],
    queryFn: async () => {
      // Mock historical price data (last 24 hours, 5-minute intervals)
      const data: PriceData[] = [];
      const now = new Date();
      const basePrice = marketData?.price || 22134.75;

      for (let i = 144; i >= 0; i--) { // 144 * 5min = 12 hours
        const timestamp = new Date(now.getTime() - i * 5 * 60 * 1000);
        const priceVariation = (Math.random() - 0.5) * 200; // ±100 variation
        const price = basePrice + priceVariation - (144 - i) * 2; // Slight downward trend
        const volume = Math.floor(Math.random() * 10000) + 5000;

        data.push({
          timestamp: timestamp.toISOString(),
          price: Math.max(0, price), // Ensure positive price
          volume,
        });
      }

      return data;
    },
    refetchInterval: autoRefresh ? 30000 : false, // Update every 30 seconds
  });

  // Order placement mutation
  const placeOrderMutation = useMutation({
    mutationFn: async (orderData: OrderFormData) => {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      return { orderId: `ORD${Date.now()}`, ...orderData };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['active-orders'] });
      // Reset form
      setOrderForm(prev => ({
        ...prev,
        quantity: 1,
        price: undefined,
        stopLoss: undefined,
        takeProfit: undefined,
        trailingStopDistance: undefined,
        ocoTargetPrice: undefined,
        ocoStopPrice: undefined,
        icebergVisibleQuantity: undefined,
        timeInForce: 'DAY',
      }));

      // Add success notification
      addNotification(
        'success',
        'Order Placed Successfully',
        `${data.side} ${data.quantity} ${data.symbol} @ ${data.price ? formatCurrency(data.price) : 'Market Price'}`
      );
    },
    onError: () => {
      addNotification(
        'error',
        'Order Failed',
        'Failed to place order. Please try again.'
      );
    },
  });

  // Cancel order mutation
  const cancelOrderMutation = useMutation({
    mutationFn: async (orderId: string) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return orderId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['active-orders'] });
    },
  });

  // Handle order form submission
  const handleOrderSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();

    // Risk management validation
    const orderValue = (orderForm.price || marketData?.price || 0) * orderForm.quantity;
    if (orderValue > riskManagement.maxSingleTrade) {
      alert(`Order value (${formatCurrency(orderValue)}) exceeds maximum single trade limit (${formatCurrency(riskManagement.maxSingleTrade)})`);
      return;
    }

    const riskAmount = (orderForm.price || marketData?.price || 0) * orderForm.quantity * (riskManagement.riskPerTrade / 100);
    if (riskAmount > riskManagement.maxPositionSize * 0.1) { // 10% of max position
      alert(`Order risk (${formatCurrency(riskAmount)}) exceeds position risk limit`);
      return;
    }

    placeOrderMutation.mutate(orderForm);
  }, [orderForm, marketData, riskManagement, placeOrderMutation]);

  // Notification functions
  const addNotification = useCallback((type: NotificationItem['type'], title: string, message: string) => {
    const notification: NotificationItem = {
      id: `notif-${Date.now()}-${Math.random()}`,
      type,
      title,
      message,
      timestamp: new Date(),
      read: false,
    };

    setNotifications(prev => [notification, ...prev].slice(0, 50)); // Keep last 50 notifications

    // Browser notification
    if (notificationsEnabled && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(title, {
        body: message,
        icon: '/favicon.ico',
      });
    }

    // Sound alert
    if (soundEnabled) {
      try {
        const audio = new Audio();
        audio.volume = 0.3;
        // Use Web Audio API for a simple beep
        const context = new (window.AudioContext || (window as any).webkitAudioContext)();
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(context.destination);

        oscillator.frequency.setValueAtTime(type === 'error' ? 300 : type === 'warning' ? 400 : 500, context.currentTime);
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.3, context.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.3);

        oscillator.start(context.currentTime);
        oscillator.stop(context.currentTime + 0.3);
      } catch (error) {
        console.warn('Sound playback failed:', error);
      }
    }
  }, [notificationsEnabled, soundEnabled]);

  const markNotificationAsRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(notif =>
      notif.id === id ? { ...notif, read: true } : notif
    ));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Handle symbol change
  const handleSymbolChange = useCallback((symbol: string) => {
    setSelectedSymbol(symbol);
    setOrderForm(prev => ({ ...prev, symbol }));
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showNotifications && !(event.target as Element).closest('.notification-dropdown')) {
        setShowNotifications(false);
      }
      if (showKeyboardShortcuts && !(event.target as Element).closest('.keyboard-shortcuts-modal')) {
        setShowKeyboardShortcuts(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showNotifications, showKeyboardShortcuts]);
  const positionSummary = React.useMemo(() => {
    if (!portfolio) return { totalValue: 0, totalPnL: 0, totalPnLPercentage: 0 };

    const totalValue = portfolio.reduce((sum, pos) => sum + Math.abs(pos.marketValue), 0);
    const totalPnL = portfolio.reduce((sum, pos) => sum + pos.unrealizedPnL + pos.realizedPnL, 0);
    const totalPnLPercentage = totalValue > 0 ? (totalPnL / totalValue) * 100 : 0;

    return { totalValue, totalPnL, totalPnLPercentage };
  }, [portfolio]);

  // WebSocket event handlers
  useEffect(() => {
    if (!isConnected) return;

    // const handleMarketData = (data: MarketData) => {
    //   if (data.symbol === selectedSymbol) {
    //     queryClient.setQueryData(['market-data', selectedSymbol], data);
    //   }
    // };

    // const handlePortfolioUpdate = (data: any) => {
    //   queryClient.invalidateQueries({ queryKey: ['portfolio'] });
    // };

    // const handleOrderUpdate = (data: any) => {
    //   queryClient.invalidateQueries({ queryKey: ['active-orders'] });
    // };

    // const handleTradeExecuted = (data: Trade) => {
    //   queryClient.invalidateQueries({ queryKey: ['recent-trades'] });
    //   queryClient.invalidateQueries({ queryKey: ['portfolio'] });

    //   if (notificationsEnabled) {
    //     // Show notification
    //     if ('Notification' in window && Notification.permission === 'granted') {
    //       new Notification(`Trade Executed: ${data.symbol}`, {
    //         body: `${data.side} ${data.quantity} @ ${formatCurrency(data.price)}`,
    //         icon: '/favicon.ico',
    //       });
    //     }
    //   }
    // };

    // Subscribe to real-time updates
    // websocketService.on('market_data', handleMarketData);
    // websocketService.on('portfolio_update', handlePortfolioUpdate);
    // websocketService.on('order_update', handleOrderUpdate);
    // websocketService.on('trade_executed', handleTradeExecuted);

    return () => {
      // Cleanup subscriptions
      // websocketService.off('market_data', handleMarketData);
      // etc.
    };
  }, [isConnected, selectedSymbol, queryClient, notificationsEnabled]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input field
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.key.toLowerCase()) {
        case 'b':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, side: 'BUY' }));
          }
          break;
        case 's':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, side: 'SELL' }));
          }
          break;
        case 'arrowup':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, quantity: prev.quantity + 1 }));
          }
          break;
        case 'arrowdown':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, quantity: Math.max(1, prev.quantity - 1) }));
          }
          break;
        case '+':
        case '=':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, quantity: prev.quantity + 1 }));
          }
          break;
        case '-':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setOrderForm(prev => ({ ...prev, quantity: Math.max(1, prev.quantity - 1) }));
          }
          break;
        case 'enter':
          if (event.ctrlKey) {
            event.preventDefault();
            handleOrderSubmit(event as any);
          }
          break;
        case 'delete':
        case 'backspace':
          if (!event.ctrlKey && !event.altKey && !event.metaKey && activeOrders && activeOrders.length > 0) {
            event.preventDefault();
            // Cancel the most recent order
            const mostRecentOrder = activeOrders[0];
            cancelOrderMutation.mutate(mostRecentOrder.orderId);
          }
          break;
        case 'f1':
          event.preventDefault();
          setIsOrderFormVisible(!isOrderFormVisible);
          break;
        case 'f2':
          event.preventDefault();
          setIsMarketDataVisible(!isMarketDataVisible);
          break;
        case 'f3':
          event.preventDefault();
          setIsIndicatorsVisible(!isIndicatorsVisible);
          break;
        case 'f4':
          event.preventDefault();
          setIsPortfolioVisible(!isPortfolioVisible);
          break;
        case 'r':
          if (event.ctrlKey) {
            event.preventDefault();
            setAutoRefresh(!autoRefresh);
          }
          break;
        case 'm':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            setViewMode(viewMode === 'compact' ? 'detailed' : 'compact');
          }
          break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
          if (!event.ctrlKey && !event.altKey && !event.metaKey) {
            event.preventDefault();
            const symbols = ['NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY'];
            const index = parseInt(event.key) - 1;
            if (index >= 0 && index < symbols.length) {
              handleSymbolChange(symbols[index]);
            }
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [orderForm, activeOrders, cancelOrderMutation, handleOrderSubmit, handleSymbolChange, isOrderFormVisible, isMarketDataVisible, isIndicatorsVisible, isPortfolioVisible, autoRefresh, viewMode]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Trading Interface
              </h1>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Symbol Selector */}
              <select
                value={selectedSymbol}
                onChange={(e) => handleSymbolChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="NIFTY50">NIFTY 50</option>
                <option value="BANKNIFTY">BANK NIFTY</option>
                <option value="RELIANCE">RELIANCE</option>
                <option value="TCS">TCS</option>
                <option value="INFY">INFOSYS</option>
              </select>

              {/* View Controls */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setViewMode(viewMode === 'compact' ? 'detailed' : 'compact')}
                  className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                  title={viewMode === 'compact' ? 'Detailed View' : 'Compact View'}
                >
                  {viewMode === 'compact' ? <Maximize2 className="w-5 h-5" /> : <Minimize2 className="w-5 h-5" />}
                </button>

                <button
                  onClick={() => setAutoRefresh(!autoRefresh)}
                  className={`p-2 ${autoRefresh ? 'text-green-600' : 'text-gray-400'}`}
                  title={autoRefresh ? 'Disable Auto Refresh' : 'Enable Auto Refresh'}
                >
                  <RefreshCw className={`w-5 h-5 ${autoRefresh ? 'animate-spin' : ''}`} />
                </button>

                <button
                  onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                  className={`p-2 ${notificationsEnabled ? 'text-blue-600' : 'text-gray-400'}`}
                  title={notificationsEnabled ? 'Disable Notifications' : 'Enable Notifications'}
                >
                  {notificationsEnabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                </button>

                <button
                  onClick={() => setSoundEnabled(!soundEnabled)}
                  className={`p-2 ${soundEnabled ? 'text-green-600' : 'text-gray-400'}`}
                  title={soundEnabled ? 'Disable Sound Alerts' : 'Enable Sound Alerts'}
                >
                  {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                </button>
              </div>

              {/* Notifications */}
              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className={`p-2 ${notificationsEnabled ? 'text-blue-600' : 'text-gray-400'} relative`}
                  title="Notifications"
                >
                  {notifications.filter(n => !n.read).length > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                      {notifications.filter(n => !n.read).length}
                    </span>
                  )}
                  <Bell className="w-5 h-5" />
                </button>

                {/* Notification Dropdown */}
                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 notification-dropdown">
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Notifications</h4>
                        <button
                          onClick={clearAllNotifications}
                          className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                        >
                          Clear All
                        </button>
                      </div>

                      {notifications.length === 0 ? (
                        <div className="text-center py-4">
                          <Bell className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-gray-500">No notifications</p>
                        </div>
                      ) : (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {notifications.map((notification) => (
                            <div
                              key={notification.id}
                              className={`p-3 rounded-lg border-l-4 ${
                                notification.type === 'success'
                                  ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
                                  : notification.type === 'error'
                                  ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                                  : notification.type === 'warning'
                                  ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20'
                                  : 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                              } ${!notification.read ? 'bg-opacity-100' : 'bg-opacity-50'}`}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                                    {notification.title}
                                  </p>
                                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                    {notification.message}
                                  </p>
                                  <p className="text-xs text-gray-500 mt-1">
                                    {formatRelativeTime(notification.timestamp.toISOString())}
                                  </p>
                                </div>
                                {!notification.read && (
                                  <button
                                    onClick={() => markNotificationAsRead(notification.id)}
                                    className="text-xs text-blue-600 hover:text-blue-800 ml-2"
                                  >
                                    Mark Read
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Keyboard Shortcuts */}
              <button
                onClick={() => setShowKeyboardShortcuts(!showKeyboardShortcuts)}
                className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                title="Keyboard Shortcuts"
              >
                <kbd className="text-xs">⌨️</kbd>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Keyboard Shortcuts Modal */}
      {showKeyboardShortcuts && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowKeyboardShortcuts(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4 keyboard-shortcuts-modal" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Keyboard Shortcuts</h3>
              <button
                onClick={() => setShowKeyboardShortcuts(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Place Order:</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">Ctrl + Enter</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Buy/Sell Toggle:</span>
                <div className="flex space-x-1">
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">B</kbd>
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">S</kbd>
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Quantity:</span>
                <div className="flex space-x-1">
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">↑↓</kbd>
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">+/-</kbd>
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Cancel Order:</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">Delete</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Symbol Switch:</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">1-5</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Toggle Panels:</span>
                <div className="flex space-x-1">
                  <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">F1-F4</kbd>
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Auto Refresh:</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">Ctrl + R</kbd>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">View Mode:</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">M</kbd>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Sidebar - Order Form */}
          <div className={`${viewMode === 'compact' ? 'lg:col-span-4' : 'lg:col-span-3'} space-y-6`}>
            {/* Order Form */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Place Order
                </h3>
                <button
                  onClick={() => setIsOrderFormVisible(!isOrderFormVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isOrderFormVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isOrderFormVisible && (
                <form onSubmit={handleOrderSubmit} className="space-y-4">
                  {/* Side Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Side
                    </label>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={() => setOrderForm(prev => ({ ...prev, side: 'BUY' }))}
                        className={`flex-1 py-2 px-4 rounded-md font-medium ${
                          orderForm.side === 'BUY'
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        BUY
                      </button>
                      <button
                        type="button"
                        onClick={() => setOrderForm(prev => ({ ...prev, side: 'SELL' }))}
                        className={`flex-1 py-2 px-4 rounded-md font-medium ${
                          orderForm.side === 'SELL'
                            ? 'bg-red-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        SELL
                      </button>
                    </div>
                  </div>

                  {/* Order Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Order Type
                    </label>
                    <select
                      value={orderForm.orderType}
                      onChange={(e) => setOrderForm(prev => ({ ...prev, orderType: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      {ORDER_TYPES.map(type => (
                        <option key={type.id} value={type.id}>
                          {type.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Time-in-Force */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Time-in-Force
                    </label>
                    <select
                      value={orderForm.timeInForce}
                      onChange={(e) => setOrderForm(prev => ({ ...prev, timeInForce: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      {TIME_IN_FORCE_OPTIONS.map(option => (
                        <option key={option.id} value={option.id}>
                          {option.name} - {option.description}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Quantity */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Quantity
                    </label>
                    <div className="flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={() => setOrderForm(prev => ({ ...prev, quantity: Math.max(1, prev.quantity - 1) }))}
                        className="p-2 bg-gray-200 dark:bg-gray-700 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <input
                        type="number"
                        value={orderForm.quantity}
                        onChange={(e) => setOrderForm(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))}
                        min="1"
                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-center"
                      />
                      <button
                        type="button"
                        onClick={() => setOrderForm(prev => ({ ...prev, quantity: prev.quantity + 1 }))}
                        className="p-2 bg-gray-200 dark:bg-gray-700 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Price (for limit orders) */}
                  {ORDER_TYPES.find(type => type.id === orderForm.orderType)?.requiresPrice && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Price
                      </label>
                      <input
                        type="number"
                        value={orderForm.price || ''}
                        onChange={(e) => setOrderForm(prev => ({ ...prev, price: parseFloat(e.target.value) || undefined }))}
                        step="0.01"
                        placeholder={`Market: ${marketData ? formatCurrency(marketData.price) : 'Loading...'}`}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                  )}

                  {/* Advanced Options based on Order Type */}
                  {orderForm.orderType === 'TRAILING_STOP' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Trailing Distance (%)
                      </label>
                      <input
                        type="number"
                        value={orderForm.trailingStopDistance || ''}
                        onChange={(e) => setOrderForm(prev => ({ ...prev, trailingStopDistance: parseFloat(e.target.value) || undefined }))}
                        step="0.1"
                        min="0.1"
                        placeholder="2.0"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                  )}

                  {orderForm.orderType === 'OCO' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Target Price
                        </label>
                        <input
                          type="number"
                          value={orderForm.ocoTargetPrice || ''}
                          onChange={(e) => setOrderForm(prev => ({ ...prev, ocoTargetPrice: parseFloat(e.target.value) || undefined }))}
                          step="0.01"
                          placeholder="Target price for profit taking"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Stop Price
                        </label>
                        <input
                          type="number"
                          value={orderForm.ocoStopPrice || ''}
                          onChange={(e) => setOrderForm(prev => ({ ...prev, ocoStopPrice: parseFloat(e.target.value) || undefined }))}
                          step="0.01"
                          placeholder="Stop price for loss protection"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                    </>
                  )}

                  {orderForm.orderType === 'BRACKET' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Stop Loss Distance (%)
                        </label>
                        <input
                          type="number"
                          value={orderForm.stopLoss || ''}
                          onChange={(e) => setOrderForm(prev => ({ ...prev, stopLoss: parseFloat(e.target.value) || undefined }))}
                          step="0.1"
                          min="0.1"
                          placeholder="1.0"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Take Profit Distance (%)
                        </label>
                        <input
                          type="number"
                          value={orderForm.takeProfit || ''}
                          onChange={(e) => setOrderForm(prev => ({ ...prev, takeProfit: parseFloat(e.target.value) || undefined }))}
                          step="0.1"
                          min="0.1"
                          placeholder="2.0"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                      </div>
                    </>
                  )}

                  {orderForm.orderType === 'ICEBERG' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Visible Quantity
                      </label>
                      <input
                        type="number"
                        value={orderForm.icebergVisibleQuantity || ''}
                        onChange={(e) => setOrderForm(prev => ({ ...prev, icebergVisibleQuantity: parseInt(e.target.value) || undefined }))}
                        min="1"
                        placeholder="Visible portion of iceberg order"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                      />
                    </div>
                  )}

                  {/* Risk Calculator */}
                  <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Risk Amount:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {(() => {
                          const basePrice = orderForm.price || marketData?.price || 0;
                          let riskAmount = 0;

                          if (orderForm.orderType === 'BRACKET') {
                            // For bracket orders, stop loss is a percentage
                            const stopLossPercent = orderForm.stopLoss || 1.0;
                            riskAmount = basePrice * orderForm.quantity * (stopLossPercent / 100);
                          } else if (orderForm.stopLoss) {
                            // For other orders, stop loss is an absolute price
                            riskAmount = Math.abs(basePrice - orderForm.stopLoss) * orderForm.quantity;
                          } else {
                            // Default risk calculation
                            riskAmount = basePrice * orderForm.quantity * (riskManagement.riskPerTrade / 100);
                          }

                          return formatCurrency(riskAmount);
                        })()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm mt-1">
                      <span className="text-gray-600 dark:text-gray-400">Potential P&L:</span>
                      <span className="font-medium text-green-600">
                        {(() => {
                          const basePrice = orderForm.price || marketData?.price || 0;
                          let potentialPnL = 0;

                          if (orderForm.orderType === 'BRACKET') {
                            // For bracket orders, take profit is a percentage
                            const takeProfitPercent = orderForm.takeProfit || 2.0;
                            potentialPnL = basePrice * orderForm.quantity * (takeProfitPercent / 100);
                          } else if (orderForm.takeProfit) {
                            // For other orders, take profit is an absolute price
                            potentialPnL = (orderForm.takeProfit - basePrice) * orderForm.quantity;
                          } else {
                            // Default calculation with 2% target
                            potentialPnL = basePrice * orderForm.quantity * 0.02;
                          }

                          return `+${formatCurrency(Math.abs(potentialPnL))}`;
                        })()}
                      </span>
                    </div>
                    {orderForm.orderType === 'TRAILING_STOP' && orderForm.trailingStopDistance && (
                      <div className="flex items-center justify-between text-sm mt-1">
                        <span className="text-gray-600 dark:text-gray-400">Trailing Stop:</span>
                        <span className="font-medium text-blue-600">
                          {orderForm.trailingStopDistance}% from peak
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={placeOrderMutation.isPending}
                    className={`w-full py-3 px-4 rounded-md font-medium text-white ${
                      orderForm.side === 'BUY'
                        ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-400'
                        : 'bg-red-600 hover:bg-red-700 disabled:bg-red-400'
                    } disabled:cursor-not-allowed flex items-center justify-center`}
                  >
                    {placeOrderMutation.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Placing Order...
                      </>
                    ) : (
                      `Place ${orderForm.side} Order`
                    )}
                  </button>
                </form>
              )}
            </div>

            {/* Risk Management Settings */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Risk Management
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Max Position Size
                  </label>
                  <div className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatCurrency(riskManagement.maxPositionSize)}
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Risk per Trade
                  </label>
                  <div className="text-lg font-medium text-gray-900 dark:text-white">
                    {riskManagement.riskPerTrade}%
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Max Daily Loss
                  </label>
                  <div className="text-lg font-medium text-gray-900 dark:text-white">
                    {formatCurrency(riskManagement.maxDailyLoss)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Center - Market Data and Charts */}
          <div className={`${viewMode === 'compact' ? 'lg:col-span-5' : 'lg:col-span-6'} space-y-6`}>
            {/* Market Data */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Market Data - {selectedSymbol}
                </h3>
                <button
                  onClick={() => setIsMarketDataVisible(!isMarketDataVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isMarketDataVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isMarketDataVisible && (
                <>
                  {marketLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                  ) : marketError ? (
                    <div className="text-center py-8">
                      <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                      <p className="text-red-600">Failed to load market data</p>
                    </div>
                  ) : marketData ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {formatCurrency(marketData.price)}
                        </div>
                        <div className="text-sm text-gray-500">Last Price</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${marketData.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {marketData.change >= 0 ? '+' : ''}{formatCurrency(marketData.change)}
                        </div>
                        <div className="text-sm text-gray-500">Change</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${marketData.change_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(marketData.change_percentage / 100)}
                        </div>
                        <div className="text-sm text-gray-500">% Change</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {formatCompactNumber(marketData.volume)}
                        </div>
                        <div className="text-sm text-gray-500">Volume</div>
                      </div>
                    </div>
                  ) : null}

                  {/* Price Chart */}
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 h-64 flex items-center justify-center">
                    {priceHistoryLoading ? (
                      <div className="flex items-center justify-center">
                        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                      </div>
                    ) : priceHistory ? (
                      <div className="w-full h-full">
                        <Line
                          data={{
                            datasets: [{
                              label: `${selectedSymbol} Price`,
                              data: priceHistory.map(point => ({
                                x: new Date(point.timestamp).getTime(),
                                y: point.price,
                              })),
                              borderColor: 'rgb(59, 130, 246)',
                              backgroundColor: 'rgba(59, 130, 246, 0.1)',
                              borderWidth: 2,
                              fill: true,
                              tension: 0.1,
                              pointRadius: 0,
                              pointHoverRadius: 4,
                            }],
                          }}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                              intersect: false,
                              mode: 'index',
                            },
                            plugins: {
                              legend: {
                                display: false,
                              },
                              tooltip: {
                                callbacks: {
                                  label: (context) => `Price: ${formatCurrency(context.parsed.y)}`,
                                },
                              },
                            },
                            scales: {
                              x: {
                                type: 'time',
                                time: {
                                  unit: 'hour',
                                  displayFormats: {
                                    hour: 'HH:mm',
                                  },
                                },
                                grid: {
                                  display: false,
                                },
                                ticks: {
                                  color: 'rgb(156, 163, 175)',
                                },
                              },
                              y: {
                                grid: {
                                  color: 'rgba(156, 163, 175, 0.1)',
                                },
                                ticks: {
                                  callback: (value) => formatCurrency(Number(value)),
                                  color: 'rgb(156, 163, 175)',
                                },
                              },
                            },
                          }}
                        />
                      </div>
                    ) : (
                      <div className="text-center">
                        <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                        <p className="text-gray-500">Unable to load price chart</p>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Technical Indicators */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Technical Indicators
                </h3>
                <button
                  onClick={() => setIsIndicatorsVisible(!isIndicatorsVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isIndicatorsVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isIndicatorsVisible && (
                <>
                  {indicatorsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                  ) : technicalIndicators ? (
                    <div className="space-y-4">
                      {/* RSI */}
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">RSI (14)</span>
                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-bold ${
                            technicalIndicators.rsi > 70 ? 'text-red-600' :
                            technicalIndicators.rsi < 30 ? 'text-green-600' :
                            'text-gray-900 dark:text-white'
                          }`}>
                            {technicalIndicators.rsi}
                          </span>
                          <div className={`w-2 h-2 rounded-full ${
                            technicalIndicators.rsi > 70 ? 'bg-red-500' :
                            technicalIndicators.rsi < 30 ? 'bg-green-500' :
                            'bg-yellow-500'
                          }`} />
                        </div>
                      </div>

                      {/* MACD */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">MACD (12,26,9)</span>
                          <span className={`text-sm font-bold ${
                            technicalIndicators.macd.histogram > 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {formatCurrency(technicalIndicators.macd.value)}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <div>Signal: {formatCurrency(technicalIndicators.macd.signal)}</div>
                          <div>Histogram: {formatCurrency(technicalIndicators.macd.histogram)}</div>
                        </div>
                      </div>

                      {/* Bollinger Bands */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Bollinger Bands (20,2)</span>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <div>Upper: {formatCurrency(technicalIndicators.bollingerBands.upper)}</div>
                          <div>Middle: {formatCurrency(technicalIndicators.bollingerBands.middle)}</div>
                          <div>Lower: {formatCurrency(technicalIndicators.bollingerBands.lower)}</div>
                        </div>
                      </div>

                      {/* Moving Averages */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Moving Averages</span>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <div>SMA(20): {formatCurrency(technicalIndicators.movingAverages.sma20)}</div>
                          <div>SMA(50): {formatCurrency(technicalIndicators.movingAverages.sma50)}</div>
                          <div>EMA(12): {formatCurrency(technicalIndicators.movingAverages.ema12)}</div>
                          <div>EMA(26): {formatCurrency(technicalIndicators.movingAverages.ema26)}</div>
                        </div>
                      </div>

                      {/* Stochastic */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Stochastic (14,3,3)</span>
                        </div>
                        <div className="text-xs text-gray-500 space-y-1">
                          <div>%K: {technicalIndicators.stochastic.k.toFixed(2)}</div>
                          <div>%D: {technicalIndicators.stochastic.d.toFixed(2)}</div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No technical indicators available</p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Portfolio Summary */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Portfolio Summary
                </h3>
                <button
                  onClick={() => setIsPortfolioVisible(!isPortfolioVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isPortfolioVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isPortfolioVisible && (
                <>
                  {portfolioLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {formatCurrency(positionSummary.totalValue)}
                        </div>
                        <div className="text-sm text-gray-500">Total Value</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${positionSummary.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(positionSummary.totalPnL)}
                        </div>
                        <div className="text-sm text-gray-500">Total P&L</div>
                      </div>
                      <div className="text-center">
                        <div className={`text-2xl font-bold ${positionSummary.totalPnLPercentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(positionSummary.totalPnLPercentage / 100)}
                        </div>
                        <div className="text-sm text-gray-500">P&L %</div>
                      </div>
                    </div>
                  )}

                  {/* Positions List */}
                  {portfolio && portfolio.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-gray-900 dark:text-white">Positions</h4>
                      {portfolio.map((position) => {
                        const pnlInfo = formatPnL(position.unrealizedPnL, position.unrealizedPnLPercentage);
                        return (
                          <div key={position.symbol} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                            <div className="flex-1">
                              <p className="font-medium text-gray-900 dark:text-white">{position.symbol}</p>
                              <p className="text-sm text-gray-500">
                                {position.quantity > 0 ? '+' : ''}{position.quantity} @ {formatCurrency(position.averagePrice)}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="font-medium text-gray-900 dark:text-white">
                                {formatCurrency(position.marketValue)}
                              </p>
                              <p className={`text-sm ${pnlInfo.color}`}>
                                {pnlInfo.value}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Right Sidebar - Orders and Trades */}
          <div className={`${viewMode === 'compact' ? 'lg:col-span-3' : 'lg:col-span-3'} space-y-6`}>
            {/* Active Orders */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Active Orders
                </h3>
                <button
                  onClick={() => setIsOrdersVisible(!isOrdersVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isOrdersVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isOrdersVisible && (
                <>
                  {ordersLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                  ) : activeOrders && activeOrders.length > 0 ? (
                    <div className="space-y-3 max-h-64 overflow-y-auto">
                      {activeOrders.map((order) => {
                        const sideInfo = formatTradeSide(order.side);
                        const statusInfo = formatTradeStatus(order.status);
                        return (
                          <div key={order.orderId} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900 dark:text-white">{order.symbol}</span>
                                <div className={`px-2 py-1 rounded-full text-xs font-medium ${sideInfo.bgColor} ${sideInfo.color}`}>
                                  {sideInfo.text}
                                </div>
                              </div>
                              <div className={`px-2 py-1 rounded-full text-xs font-medium ${statusInfo.bgColor} ${statusInfo.color}`}>
                                {statusInfo.text}
                              </div>
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                              {order.quantity} @ {order.price ? formatCurrency(order.price) : 'Market'}
                            </div>
                            <div className="flex items-center justify-between mt-2">
                              <span className="text-xs text-gray-500">{formatRelativeTime(order.timestamp)}</span>
                              <button
                                onClick={() => cancelOrderMutation.mutate(order.orderId)}
                                disabled={cancelOrderMutation.isPending}
                                className="text-xs text-red-600 hover:text-red-800 disabled:text-red-400"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No active orders</p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Recent Trades */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Recent Trades
                </h3>
                <button
                  onClick={() => setIsTradesVisible(!isTradesVisible)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isTradesVisible ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>

              {isTradesVisible && (
                <>
                  {tradesLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                    </div>
                  ) : recentTrades && recentTrades.length > 0 ? (
                    <div className="space-y-3 max-h-64 overflow-y-auto">
                      {recentTrades.map((trade) => {
                        const sideInfo = formatTradeSide(trade.side);
                        return (
                          <div key={trade.tradeId} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900 dark:text-white">{trade.symbol}</span>
                                <div className={`px-2 py-1 rounded-full text-xs font-medium ${sideInfo.bgColor} ${sideInfo.color}`}>
                                  {sideInfo.text}
                                </div>
                              </div>
                              {trade.pnl !== undefined && (
                                <span className={`text-sm font-medium ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {formatCurrency(trade.pnl)}
                                </span>
                              )}
                            </div>
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                              {trade.quantity} @ {formatCurrency(trade.price)}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatRelativeTime(trade.timestamp)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-gray-500">No recent trades</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center text-sm text-gray-500 dark:text-gray-400">
            <div>
              Last updated: {formatDateTime(new Date().toISOString())}
            </div>
            <div className="flex items-center space-x-4">
              <span>Trading Mode: Paper</span>
              <span>Connection: {isConnected ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default TradingInterface;
