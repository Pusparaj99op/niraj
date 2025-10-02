/**
 * WebSocket Service Test Component
 *
 * This component tests the WebSocket service functionality including:
 * - Connection management
 * - Authentication
 * - Stream subscriptions
 * - Error handling
 * - Automatic reconnection
 */

import React, { useState, useEffect } from 'react';
import { useWebSocket, useMarketData, usePortfolioUpdates, useTradeSignals } from '../hooks/useWebSocket';

const WebSocketTestComponent: React.FC = () => {
  const [token, setToken] = useState('');
  const [selectedSymbols] = useState<string[]>(['AAPL', 'GOOGL']);
  const [logs, setLogs] = useState<string[]>([]);

  // Main WebSocket hook
  const {
    connectionState,
    isConnected,
    isAuthenticated,
    lastError,
    metrics,
    connect,
    disconnect,
    subscribeToMarketData,
    onError,
    onConnectionStateChange
  } = useWebSocket();

  // Specialized hooks
  const { marketData, isSubscribed: marketDataSubscribed } = useMarketData(
    selectedSymbols,
    '15min',
    { autoSubscribe: isAuthenticated }
  );

  const { portfolioData, isSubscribed: portfolioSubscribed } = usePortfolioUpdates({
    autoSubscribe: isAuthenticated
  });

  const { tradeSignals, isSubscribed: signalsSubscribed, clearSignals } = useTradeSignals({
    minConfidence: 0.7,
    autoSubscribe: isAuthenticated
  });

  // Logging helper
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 50)); // Keep last 50 logs
  };

  // Set up event handlers
  useEffect(() => {
    const cleanupError = onError((error) => {
      addLog(`ERROR: ${error.error_code} - ${error.error_message}`);
    });

    const cleanupState = onConnectionStateChange((state) => {
      addLog(`Connection state changed: ${state}`);
    });

    return () => {
      cleanupError();
      cleanupState();
    };
  }, [onError, onConnectionStateChange]);

  // Log market data updates
  useEffect(() => {
    if (marketData.size > 0) {
      const symbols = Array.from(marketData.keys()).join(', ');
      addLog(`Market data updated for: ${symbols}`);
    }
  }, [marketData]);

  // Log portfolio updates
  useEffect(() => {
    if (portfolioData) {
      addLog(`Portfolio updated: $${portfolioData.total_value.toFixed(2)} total value`);
    }
  }, [portfolioData]);

  // Log trade signals
  useEffect(() => {
    if (tradeSignals.length > 0) {
      const latest = tradeSignals[0];
      addLog(`New trade signal: ${latest.action} ${latest.symbol} (confidence: ${latest.confidence})`);
    }
  }, [tradeSignals]);

  // Manual connection handlers
  const handleConnect = async () => {
    try {
      addLog('Attempting to connect...');
      await connect(token || undefined);
      addLog('Connect request sent');
    } catch (error) {
      addLog(`Connect failed: ${error}`);
    }
  };

  const handleDisconnect = () => {
    addLog('Disconnecting...');
    disconnect();
  };

  // Manual subscription test
  const handleManualSubscribe = async () => {
    try {
      addLog('Manual subscription test...');
      const subscriptionId = await subscribeToMarketData({
        symbols: ['TSLA', 'MSFT'],
        timeframe: '5min'
      });
      addLog(`Manual subscription created: ${subscriptionId}`);
    } catch (error) {
      addLog(`Manual subscription failed: ${error}`);
    }
  };

  // Get connection status color
  const getStatusColor = () => {
    switch (connectionState) {
      case 'connected': return 'text-green-500';
      case 'authenticated': return 'text-green-600';
      case 'connecting':
      case 'reconnecting': return 'text-yellow-500';
      case 'error': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">WebSocket Service Test</h1>

      {/* Connection Status */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="text-xl font-semibold mb-4">Connection Status</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">State</label>
            <span className={`text-lg font-semibold ${getStatusColor()}`}>
              {connectionState}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Connected</label>
            <span className={`text-lg font-semibold ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
              {isConnected ? 'Yes' : 'No'}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Authenticated</label>
            <span className={`text-lg font-semibold ${isAuthenticated ? 'text-green-500' : 'text-red-500'}`}>
              {isAuthenticated ? 'Yes' : 'No'}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Messages</label>
            <span className="text-lg font-semibold text-blue-500">
              {metrics.totalMessages}
            </span>
          </div>
        </div>

        {lastError && (
          <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded">
            <p className="text-red-700">
              <strong>{lastError.error_code}:</strong> {lastError.error_message}
            </p>
          </div>
        )}
      </div>

      {/* Connection Controls */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="text-xl font-semibold mb-4">Connection Controls</h2>
        <div className="flex flex-wrap gap-4 mb-4">
          <input
            type="text"
            placeholder="JWT Token (optional)"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="flex-1 min-w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleConnect}
            disabled={isConnected}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
          >
            Connect
          </button>
          <button
            onClick={handleDisconnect}
            disabled={!isConnected}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-400"
          >
            Disconnect
          </button>
          <button
            onClick={handleManualSubscribe}
            disabled={!isAuthenticated}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400"
          >
            Test Subscribe
          </button>
        </div>
      </div>

      {/* Subscription Status */}
      <div className="bg-white rounded-lg shadow-md p-4 mb-6">
        <h2 className="text-xl font-semibold mb-4">Subscription Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3 border rounded">
            <h3 className="font-medium">Market Data</h3>
            <p className={`text-sm ${marketDataSubscribed ? 'text-green-500' : 'text-red-500'}`}>
              {marketDataSubscribed ? 'Subscribed' : 'Not subscribed'}
            </p>
            <p className="text-xs text-gray-500">
              Symbols: {selectedSymbols.join(', ')}
            </p>
            <p className="text-xs text-gray-500">
              Updates: {marketData.size}
            </p>
          </div>
          <div className="p-3 border rounded">
            <h3 className="font-medium">Portfolio</h3>
            <p className={`text-sm ${portfolioSubscribed ? 'text-green-500' : 'text-red-500'}`}>
              {portfolioSubscribed ? 'Subscribed' : 'Not subscribed'}
            </p>
            <p className="text-xs text-gray-500">
              Last update: {portfolioData ? new Date(portfolioData.timestamp).toLocaleTimeString() : 'None'}
            </p>
          </div>
          <div className="p-3 border rounded">
            <h3 className="font-medium">Trade Signals</h3>
            <p className={`text-sm ${signalsSubscribed ? 'text-green-500' : 'text-red-500'}`}>
              {signalsSubscribed ? 'Subscribed' : 'Not subscribed'}
            </p>
            <p className="text-xs text-gray-500">
              Signals: {tradeSignals.length}
            </p>
            {tradeSignals.length > 0 && (
              <button
                onClick={clearSignals}
                className="text-xs text-blue-500 hover:text-blue-700"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Market Data Display */}
      {marketData.size > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <h2 className="text-xl font-semibold mb-4">Market Data</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Symbol</th>
                  <th className="text-left p-2">Price</th>
                  <th className="text-left p-2">Change %</th>
                  <th className="text-left p-2">Volume</th>
                  <th className="text-left p-2">Last Update</th>
                </tr>
              </thead>
              <tbody>
                {Array.from(marketData.entries()).map(([symbol, data]) => (
                  <tr key={symbol} className="border-b">
                    <td className="p-2 font-medium">{symbol}</td>
                    <td className="p-2">${data.ohlcv.close.toFixed(2)}</td>
                    <td className={`p-2 ${data.ohlcv.change_percent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {data.ohlcv.change_percent.toFixed(2)}%
                    </td>
                    <td className="p-2">{data.ohlcv.volume.toLocaleString()}</td>
                    <td className="p-2">{new Date(data.ohlcv.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Trade Signals */}
      {tradeSignals.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4 mb-6">
          <h2 className="text-xl font-semibold mb-4">Recent Trade Signals</h2>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {tradeSignals.slice(0, 10).map((signal, index) => (
              <div key={index} className="p-3 border rounded text-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <span className={`font-medium ${signal.action === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                      {signal.action}
                    </span>
                    <span className="ml-2 font-medium">{signal.symbol}</span>
                    <span className="ml-2 text-gray-500">@${signal.price.toFixed(2)}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-blue-500">{(signal.confidence * 100).toFixed(1)}%</div>
                    <div className="text-xs text-gray-500">
                      {new Date(signal.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-gray-600 mt-1">{signal.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Logs */}
      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Event Logs</h2>
          <button
            onClick={() => setLogs([])}
            className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Clear Logs
          </button>
        </div>
        <div className="bg-gray-100 rounded p-3 h-64 overflow-y-auto font-mono text-sm">
          {logs.length === 0 ? (
            <p className="text-gray-500">No logs yet...</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="mb-1 text-gray-800">
                {log}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default WebSocketTestComponent;
