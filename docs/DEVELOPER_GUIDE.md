# NIRAJ Developer Guide

## Overview

This comprehensive guide covers development setup, coding standards, testing practices, and contribution guidelines for the NIRAJ trading system. Whether you're a core contributor or external developer, this guide will help you build high-quality, maintainable code.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Testing Guidelines](#testing-guidelines)
5. [API Development](#api-development)
6. [Frontend Development](#frontend-development)
7. [Database Development](#database-development)
8. [AI/ML Development](#aiml-development)
9. [Performance Guidelines](#performance-guidelines)
10. [Security Guidelines](#security-guidelines)
11. [Debugging and Profiling](#debugging-and-profiling)
12. [Contributing](#contributing)
13. [Code Reviews](#code-reviews)
14. [Release Process](#release-process)

---

## Development Environment Setup

### Prerequisites Installation

#### System Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Git 2.30+
- Docker & Docker Compose

#### Automated Setup
```bash
# Clone the repository
git clone https://github.com/Pusparaj99op/NIRAJ.git
cd NIRAJ

# Run automated setup
./scripts/setup_dev.sh

# Verify installation
./scripts/verify_setup.sh
```

#### Manual Setup

##### Python Environment
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Create virtual environment
cd backend/
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
poetry install --with dev,test

# Install pre-commit hooks
pre-commit install
```

##### Node.js Environment
```bash
cd frontend/

# Install dependencies
npm install

# Install development tools
npm install -g @typescript-eslint/eslint-plugin prettier
```

##### Database Setup
```bash
# PostgreSQL
sudo -u postgres createdb niraj_dev
sudo -u postgres createuser niraj_dev
sudo -u postgres psql -c "ALTER USER niraj_dev PASSWORD 'dev_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE niraj_dev TO niraj_dev;"

# Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

##### AI Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve &

# Pull development model
ollama pull gemma3:4b-it-q4_K_M
```

### IDE Configuration

#### VS Code Setup
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./backend/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "typescript.preferences.quoteStyle": "single",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true,
    "source.fixAll.eslint": true
  },
  "files.associations": {
    "*.yaml": "yaml",
    "*.yml": "yaml"
  }
}
```

#### Recommended Extensions
```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.pylint",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode.docker"
  ]
}
```

### Environment Configuration

#### Development Environment Variables
```bash
# backend/.env.dev
DATABASE_URL=postgresql://niraj_dev:dev_password@localhost:5432/niraj_dev
REDIS_URL=redis://localhost:6379/1
OLLAMA_BASE_URL=http://localhost:11434
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
JWT_SECRET_KEY=dev_secret_key_do_not_use_in_production
PIN_CODE=1937

# API Keys for development (use test accounts)
ANGEL_ONE_API_KEY=test_api_key
ANGEL_ONE_SECRET_KEY=test_secret_key
DHAN_CLIENT_ID=test_client_id
DHAN_ACCESS_TOKEN=test_access_token
```

```bash
# frontend/.env.dev
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENVIRONMENT=development
VITE_DEBUG=true
```

---

## Project Structure

### Backend Structure
```
backend/
├── src/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API layer
│   │   ├── routes/               # API route definitions
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── strategies.py     # Strategy management
│   │   │   ├── trades.py         # Trading operations
│   │   │   ├── portfolio.py      # Portfolio management
│   │   │   └── system.py         # System endpoints
│   │   ├── websocket_server.py   # WebSocket implementation
│   │   ├── angel_one_client.py   # Angel One API client
│   │   ├── dhan_client.py        # Dhan API client
│   │   ├── news_client.py        # News API client
│   │   ├── weather_client.py     # Weather API client
│   │   └── auth_manager.py       # API authentication manager
│   ├── core/                     # Core business logic
│   │   ├── database.py           # Database configuration
│   │   ├── database_manager.py   # Database operations
│   │   ├── cache.py              # Redis cache implementation
│   │   ├── config.py             # Configuration management
│   │   ├── data_manager.py       # Data management
│   │   ├── information_processor.py # Information processing
│   │   └── execution_engine.py   # Trade execution engine
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── base.py               # Base model class
│   │   ├── user.py               # User model
│   │   ├── strategy.py           # Strategy model
│   │   ├── trade.py              # Trade model
│   │   ├── portfolio.py          # Portfolio model
│   │   ├── market_data.py        # Market data model
│   │   ├── ai_model.py           # AI model definitions
│   │   └── audit_log.py          # Audit logging model
│   ├── services/                 # Business services
│   │   ├── auth_service.py       # Authentication service
│   │   ├── user_service.py       # User management
│   │   ├── config_service.py     # Configuration service
│   │   └── audit_service.py      # Audit service
│   ├── strategies/               # Trading strategies
│   │   ├── base_strategy.py      # Base strategy interface
│   │   ├── predatory/            # Predatory strategies
│   │   ├── quantitative/         # Quantitative strategies
│   │   ├── psychological/        # Psychological strategies
│   │   └── mathematical/         # Mathematical strategies
│   ├── ai/                       # AI/ML components
│   │   ├── gemma3_integration.py # Ollama Gemma3 client
│   │   ├── rag_processor.py      # RAG implementation
│   │   ├── confidence_tracker.py # Confidence tracking
│   │   └── learning_engine.py    # Learning pipeline
│   └── utils/                    # Utility functions
│       ├── logger.py             # Logging configuration
│       ├── technical_indicators.py # Technical indicators
│       ├── validators.py         # Input validation
│       └── helpers.py            # General helpers
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── contract/                 # Contract tests
│   └── conftest.py               # Test configuration
├── alembic/                      # Database migrations
├── config/                       # Configuration files
│   ├── development.yaml
│   ├── testing.yaml
│   └── production.yaml
├── scripts/                      # Development scripts
├── docs/                         # Documentation
├── pyproject.toml                # Python dependencies
└── README.md                     # Backend documentation
```

### Frontend Structure
```
frontend/
├── src/                          # Main application code
│   ├── main.tsx                  # Application entry point
│   ├── App.tsx                   # Main App component
│   ├── components/               # React components
│   │   ├── Dashboard.tsx         # Main dashboard
│   │   ├── AIMonitor.tsx         # AI monitoring
│   │   ├── TradingInterface.tsx  # Trading interface
│   │   ├── StrategyPerformance.tsx # Strategy performance
│   │   └── common/               # Shared components
│   │       ├── Button.tsx
│   │       ├── Modal.tsx
│   │       ├── Chart.tsx
│   │       └── Table.tsx
│   ├── hooks/                    # Custom React hooks
│   │   ├── useWebSocket.ts       # WebSocket hook
│   │   ├── useAuth.ts            # Authentication hook
│   │   ├── useApi.ts             # API hook
│   │   └── useLocalStorage.ts    # Local storage hook
│   ├── services/                 # API services
│   │   ├── api.ts                # Main API client
│   │   ├── auth.ts               # Authentication service
│   │   ├── websocket.ts          # WebSocket service
│   │   ├── strategies.ts         # Strategy service
│   │   └── portfolio.ts          # Portfolio service
│   ├── types/                    # TypeScript type definitions
│   │   ├── api.ts                # API response types
│   │   ├── auth.ts               # Authentication types
│   │   ├── strategy.ts           # Strategy types
│   │   ├── trade.ts              # Trade types
│   │   └── common.ts             # Common types
│   ├── utils/                    # Utility functions
│   │   ├── formatters.ts         # Data formatters
│   │   ├── validators.ts         # Input validation
│   │   ├── constants.ts          # Application constants
│   │   └── helpers.ts            # General helpers
│   ├── styles/                   # CSS styles
│   │   ├── globals.css           # Global styles
│   │   ├── components.css        # Component styles
│   │   └── variables.css         # CSS variables
│   └── assets/                   # Static assets
│       ├── images/
│       ├── icons/
│       └── fonts/
├── public/                       # Public assets
├── tests/                        # Frontend tests
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript configuration
├── vite.config.ts                # Vite configuration
├── tailwind.config.js            # Tailwind CSS configuration
└── README.md                     # Frontend documentation
```

---

## Coding Standards

### Python Coding Standards

#### Code Formatting
```python
# Use Black for formatting
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
```

#### Import Organization
```python
# Standard library imports
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

# Third-party imports
import pandas as pd
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

# Local imports
from src.core.database_manager import DatabaseManager
from src.models.user import User
from src.services.auth_service import AuthenticationService
from src.utils.logger import get_logger
```

#### Type Hints
```python
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel

class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    performance_metrics: Optional[Dict[str, float]] = None
    is_active: bool = False

async def get_strategy(
    strategy_id: str,
    db: DatabaseManager = Depends(get_database)
) -> StrategyResponse:
    """
    Retrieve a trading strategy by ID.

    Args:
        strategy_id: Unique identifier for the strategy
        db: Database manager instance

    Returns:
        StrategyResponse: Strategy data and metadata

    Raises:
        HTTPException: If strategy not found or access denied
    """
    strategy = await db.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return StrategyResponse.from_orm(strategy)
```

#### Error Handling
```python
import logging
from typing import Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class TradingError(Exception):
    """Base exception for trading operations"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class InsufficientFundsError(TradingError):
    """Raised when insufficient funds for trade"""
    pass

class InvalidStrategyError(TradingError):
    """Raised when strategy configuration is invalid"""
    pass

async def execute_trade(trade_data: dict) -> dict:
    try:
        # Validate trade data
        if not trade_data.get('symbol'):
            raise ValueError("Symbol is required")

        # Execute trade logic
        result = await broker_api.place_order(trade_data)

        logger.info(f"Trade executed successfully: {result['order_id']}")
        return result

    except InsufficientFundsError as e:
        logger.warning(f"Insufficient funds for trade: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)

    except InvalidStrategyError as e:
        logger.error(f"Invalid strategy configuration: {e.message}")
        raise HTTPException(status_code=422, detail=e.message)

    except Exception as e:
        logger.error(f"Unexpected error in trade execution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Async Programming
```python
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class DataManager:
    def __init__(self):
        self._connection_pool = None

    async def initialize(self) -> None:
        """Initialize database connection pool"""
        self._connection_pool = await create_pool()

    async def close(self) -> None:
        """Close database connections"""
        if self._connection_pool:
            await self._connection_pool.close()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator:
        """Context manager for database connections"""
        async with self._connection_pool.acquire() as conn:
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise
            else:
                await conn.commit()

    async def fetch_market_data(self, symbol: str) -> dict:
        """Fetch market data for symbol"""
        async with self.get_connection() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM market_data WHERE symbol = $1 ORDER BY timestamp DESC LIMIT 1",
                symbol
            )
            return dict(result) if result else {}
```

### TypeScript Coding Standards

#### Component Structure
```typescript
// components/TradingInterface.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuth } from '../hooks/useAuth';
import { TradeData, OrderType, MarketData } from '../types/trade';
import { formatCurrency, formatPercent } from '../utils/formatters';
import { Button } from './common/Button';
import { Modal } from './common/Modal';

interface TradingInterfaceProps {
  symbol: string;
  onTradeExecuted?: (trade: TradeData) => void;
  className?: string;
}

interface TradingInterfaceState {
  orderType: OrderType;
  quantity: number;
  price: number;
  isLoading: boolean;
  error: string | null;
}

export const TradingInterface: React.FC<TradingInterfaceProps> = ({
  symbol,
  onTradeExecuted,
  className = ''
}) => {
  // State management
  const [state, setState] = useState<TradingInterfaceState>({
    orderType: 'market',
    quantity: 0,
    price: 0,
    isLoading: false,
    error: null
  });

  // Custom hooks
  const { user, isAuthenticated } = useAuth();
  const { sendMessage, lastMessage } = useWebSocket();

  // Event handlers
  const handleOrderSubmit = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();

    if (!isAuthenticated) {
      setState(prev => ({ ...prev, error: 'Please log in first' }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const tradeData: TradeData = {
        symbol,
        orderType: state.orderType,
        quantity: state.quantity,
        price: state.orderType === 'limit' ? state.price : undefined
      };

      const response = await tradingService.executeTrade(tradeData);

      onTradeExecuted?.(response.data);

      // Reset form
      setState(prev => ({
        ...prev,
        quantity: 0,
        price: 0,
        isLoading: false
      }));

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Trade execution failed',
        isLoading: false
      }));
    }
  }, [symbol, isAuthenticated, state.orderType, state.quantity, state.price, onTradeExecuted]);

  // Effects
  useEffect(() => {
    // Subscribe to market data updates
    sendMessage({
      type: 'subscribe',
      stream: 'market_data',
      symbols: [symbol]
    });

    return () => {
      sendMessage({
        type: 'unsubscribe',
        stream: 'market_data'
      });
    };
  }, [symbol, sendMessage]);

  // Render
  return (
    <div className={`trading-interface ${className}`}>
      <form onSubmit={handleOrderSubmit} className="space-y-4">
        {/* Form fields */}
        <div className="grid grid-cols-2 gap-4">
          <select
            value={state.orderType}
            onChange={(e) => setState(prev => ({
              ...prev,
              orderType: e.target.value as OrderType
            }))}
            className="form-select"
          >
            <option value="market">Market Order</option>
            <option value="limit">Limit Order</option>
            <option value="stop">Stop Order</option>
          </select>

          <input
            type="number"
            placeholder="Quantity"
            value={state.quantity || ''}
            onChange={(e) => setState(prev => ({
              ...prev,
              quantity: parseInt(e.target.value) || 0
            }))}
            className="form-input"
            required
          />
        </div>

        {state.error && (
          <div className="error-message">
            {state.error}
          </div>
        )}

        <Button
          type="submit"
          disabled={state.isLoading || !state.quantity}
          loading={state.isLoading}
          className="w-full"
        >
          {state.isLoading ? 'Executing...' : 'Execute Trade'}
        </Button>
      </form>
    </div>
  );
};

export default TradingInterface;
```

#### API Service Structure
```typescript
// services/api.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiResponse, ApiError } from '../types/api';

class ApiService {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle token expiration
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: any): ApiError {
    if (error.response) {
      return {
        message: error.response.data.message || 'An error occurred',
        status: error.response.status,
        data: error.response.data
      };
    } else if (error.request) {
      return {
        message: 'Network error - please check your connection',
        status: 0,
        data: null
      };
    } else {
      return {
        message: error.message || 'An unexpected error occurred',
        status: 0,
        data: null
      };
    }
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.get<T>(url, config);
    return {
      data: response.data,
      status: response.status,
      message: 'Success'
    };
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.post<T>(url, data, config);
    return {
      data: response.data,
      status: response.status,
      message: 'Success'
    };
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.put<T>(url, data, config);
    return {
      data: response.data,
      status: response.status,
      message: 'Success'
    };
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.delete<T>(url, config);
    return {
      data: response.data,
      status: response.status,
      message: 'Success'
    };
  }
}

export const apiService = new ApiService(import.meta.env.VITE_API_BASE_URL);
export default apiService;
```

---

## Testing Guidelines

### Testing Strategy

#### Test Pyramid
```
         /\
        /  \     Unit Tests (70%)
       /____\    - Fast execution
      /      \   - Isolated components
     / Integration \ (20%)
    /   Tests      \  - Service integration
   /______________\ - Database interactions
   |              |
   |  End-to-End  | (10%)
   |    Tests     | - Full workflow
   |______________|  - User scenarios
```

### Backend Testing

#### Unit Testing with Pytest
```python
# tests/unit/test_strategy_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.strategy_service import StrategyService
from src.models.strategy import Strategy
from src.core.database_manager import DatabaseManager

@pytest.fixture
async def mock_db():
    """Mock database manager"""
    db = Mock(spec=DatabaseManager)
    db.get_strategy = AsyncMock()
    db.create_strategy = AsyncMock()
    db.update_strategy = AsyncMock()
    return db

@pytest.fixture
def strategy_service(mock_db):
    """Strategy service with mocked dependencies"""
    return StrategyService(mock_db)

@pytest.fixture
def sample_strategy():
    """Sample strategy data"""
    return Strategy(
        id="test-strategy-1",
        name="Test Strategy",
        description="A test strategy",
        category="quantitative",
        risk_level="medium",
        parameters={"stop_loss": 0.02, "take_profit": 0.05},
        is_active=True
    )

class TestStrategyService:
    async def test_get_strategy_success(self, strategy_service, mock_db, sample_strategy):
        """Test successful strategy retrieval"""
        # Arrange
        mock_db.get_strategy.return_value = sample_strategy

        # Act
        result = await strategy_service.get_strategy("test-strategy-1")

        # Assert
        assert result is not None
        assert result.id == "test-strategy-1"
        assert result.name == "Test Strategy"
        mock_db.get_strategy.assert_called_once_with("test-strategy-1")

    async def test_get_strategy_not_found(self, strategy_service, mock_db):
        """Test strategy not found scenario"""
        # Arrange
        mock_db.get_strategy.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Strategy not found"):
            await strategy_service.get_strategy("nonexistent-strategy")

    async def test_create_strategy_success(self, strategy_service, mock_db, sample_strategy):
        """Test successful strategy creation"""
        # Arrange
        strategy_data = {
            "name": "New Strategy",
            "description": "A new strategy",
            "category": "predatory",
            "risk_level": "high",
            "parameters": {"position_size": 0.1}
        }
        mock_db.create_strategy.return_value = sample_strategy

        # Act
        result = await strategy_service.create_strategy(strategy_data)

        # Assert
        assert result is not None
        mock_db.create_strategy.assert_called_once()

    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"name": ""}, "Strategy name is required"),
        ({"name": "Test", "risk_level": "invalid"}, "Invalid risk level"),
        ({"name": "Test", "parameters": "invalid"}, "Parameters must be a dictionary")
    ])
    async def test_create_strategy_validation_errors(
        self, strategy_service, invalid_data, expected_error
    ):
        """Test strategy creation validation"""
        with pytest.raises(ValueError, match=expected_error):
            await strategy_service.create_strategy(invalid_data)
```

#### Integration Testing
```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from src.main import app
from src.core.database_manager import DatabaseManager

@pytest.fixture
async def client():
    """Test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_client(client):
    """Authenticated test client"""
    # Login and get token
    login_data = {"username": "testuser", "password": "testpassword"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["access_token"]

    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

class TestStrategyEndpoints:
    async def test_get_strategies_unauthorized(self, client):
        """Test getting strategies without authentication"""
        response = await client.get("/api/v1/strategies")
        assert response.status_code == 401

    async def test_get_strategies_success(self, authenticated_client):
        """Test getting strategies with authentication"""
        response = await authenticated_client.get("/api/v1/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert isinstance(data["strategies"], list)

    async def test_create_strategy_success(self, authenticated_client):
        """Test creating a new strategy"""
        strategy_data = {
            "name": "Test Integration Strategy",
            "description": "Integration test strategy",
            "category": "quantitative",
            "risk_level": "medium",
            "parameters": {
                "stop_loss": 0.02,
                "take_profit": 0.05
            }
        }

        response = await authenticated_client.post(
            "/api/v1/strategies",
            json=strategy_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == strategy_data["name"]
        assert "id" in data

    async def test_create_strategy_validation_error(self, authenticated_client):
        """Test strategy creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "category": "invalid_category"
        }

        response = await authenticated_client.post(
            "/api/v1/strategies",
            json=invalid_data
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
```

#### Contract Testing
```python
# tests/contract/test_auth_login.py
import pytest
from httpx import AsyncClient
from src.main import app

class TestAuthLoginContract:
    """Contract tests for POST /api/v1/auth/login"""

    async def test_login_request_schema(self):
        """Test login request matches expected schema"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Valid request
            valid_request = {
                "username": "testuser",
                "password": "testpassword"
            }
            response = await client.post("/api/v1/auth/login", json=valid_request)

            # Should not return 422 (validation error)
            assert response.status_code != 422

    async def test_login_response_schema(self):
        """Test login response matches expected schema"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "username": "testuser",
                "password": "testpassword"
            }
            response = await client.post("/api/v1/auth/login", json=request_data)

            if response.status_code == 200:
                data = response.json()

                # Required fields
                assert "access_token" in data
                assert "token_type" in data
                assert "expires_in" in data
                assert "user" in data

                # Field types
                assert isinstance(data["access_token"], str)
                assert isinstance(data["token_type"], str)
                assert isinstance(data["expires_in"], int)
                assert isinstance(data["user"], dict)

                # User object schema
                user = data["user"]
                assert "id" in user
                assert "username" in user
                assert "role" in user
                assert "is_live_trading_enabled" in user

    async def test_login_error_response_schema(self):
        """Test login error response matches expected schema"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            invalid_request = {
                "username": "invalid",
                "password": "invalid"
            }
            response = await client.post("/api/v1/auth/login", json=invalid_request)

            if response.status_code == 401:
                data = response.json()

                # Error response schema
                assert "error" in data
                assert "message" in data
                assert isinstance(data["error"], str)
                assert isinstance(data["message"], str)
```

### Frontend Testing

#### Unit Testing with Jest and React Testing Library
```typescript
// tests/components/TradingInterface.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import { TradingInterface } from '../../src/components/TradingInterface';
import { AuthProvider } from '../../src/contexts/AuthContext';
import { WebSocketProvider } from '../../src/contexts/WebSocketContext';

// Mock dependencies
jest.mock('../../src/services/tradingService', () => ({
  executeTrade: jest.fn()
}));

const MockProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <WebSocketProvider>
      {children}
    </WebSocketProvider>
  </AuthProvider>
);

describe('TradingInterface', () => {
  const defaultProps = {
    symbol: 'BANKNIFTY',
    onTradeExecuted: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders trading interface correctly', () => {
    render(
      <MockProviders>
        <TradingInterface {...defaultProps} />
      </MockProviders>
    );

    expect(screen.getByText('Market Order')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Quantity')).toBeInTheDocument();
    expect(screen.getByText('Execute Trade')).toBeInTheDocument();
  });

  it('handles order type change', () => {
    render(
      <MockProviders>
        <TradingInterface {...defaultProps} />
      </MockProviders>
    );

    const orderTypeSelect = screen.getByDisplayValue('Market Order');
    fireEvent.change(orderTypeSelect, { target: { value: 'limit' } });

    expect(screen.getByDisplayValue('Limit Order')).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    render(
      <MockProviders>
        <TradingInterface {...defaultProps} />
      </MockProviders>
    );

    const submitButton = screen.getByText('Execute Trade');
    fireEvent.click(submitButton);

    // Button should be disabled when quantity is 0
    expect(submitButton).toBeDisabled();
  });

  it('executes trade successfully', async () => {
    const mockExecuteTrade = require('../../src/services/tradingService').executeTrade;
    mockExecuteTrade.mockResolvedValue({
      data: { id: 'trade-123', status: 'executed' }
    });

    render(
      <MockProviders>
        <TradingInterface {...defaultProps} />
      </MockProviders>
    );

    // Fill in form
    const quantityInput = screen.getByPlaceholderText('Quantity');
    fireEvent.change(quantityInput, { target: { value: '100' } });

    // Submit form
    const submitButton = screen.getByText('Execute Trade');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockExecuteTrade).toHaveBeenCalledWith({
        symbol: 'BANKNIFTY',
        orderType: 'market',
        quantity: 100,
        price: undefined
      });
    });

    expect(defaultProps.onTradeExecuted).toHaveBeenCalledWith({
      id: 'trade-123',
      status: 'executed'
    });
  });

  it('handles trade execution error', async () => {
    const mockExecuteTrade = require('../../src/services/tradingService').executeTrade;
    mockExecuteTrade.mockRejectedValue(new Error('Insufficient funds'));

    render(
      <MockProviders>
        <TradingInterface {...defaultProps} />
      </MockProviders>
    );

    // Fill in form
    const quantityInput = screen.getByPlaceholderText('Quantity');
    fireEvent.change(quantityInput, { target: { value: '100' } });

    // Submit form
    const submitButton = screen.getByText('Execute Trade');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Insufficient funds')).toBeInTheDocument();
    });
  });
});
```

#### Integration Testing with Playwright
```typescript
// tests/e2e/trading-workflow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Trading Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="username"]', 'testuser');
    await page.fill('[data-testid="password"]', 'testpassword');
    await page.click('[data-testid="login-button"]');

    // Wait for dashboard to load
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
  });

  test('should execute a market order successfully', async ({ page }) => {
    // Navigate to trading interface
    await page.goto('/trading');

    // Wait for trading interface to load
    await expect(page.locator('[data-testid="trading-interface"]')).toBeVisible();

    // Fill in trade details
    await page.selectOption('[data-testid="order-type"]', 'market');
    await page.fill('[data-testid="quantity"]', '100');

    // Execute trade
    await page.click('[data-testid="execute-trade"]');

    // Wait for confirmation
    await expect(page.locator('[data-testid="trade-success"]')).toBeVisible();

    // Verify trade appears in portfolio
    await page.goto('/portfolio');
    await expect(page.locator('[data-testid="trade-list"]')).toContainText('BANKNIFTY');
  });

  test('should handle validation errors', async ({ page }) => {
    await page.goto('/trading');

    // Try to execute trade without quantity
    await page.click('[data-testid="execute-trade"]');

    // Should show validation error
    await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();
  });

  test('should update real-time data', async ({ page }) => {
    await page.goto('/dashboard');

    // Check that market data is updating
    const priceElement = page.locator('[data-testid="current-price"]');
    const initialPrice = await priceElement.textContent();

    // Wait for WebSocket update (market data should change)
    await page.waitForTimeout(5000);

    const updatedPrice = await priceElement.textContent();
    // In real market hours, price should update
    // For testing, we can mock WebSocket updates
  });
});
```

### Testing Configuration

#### Pytest Configuration
```ini
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts =
    -ra
    -q
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    contract: Contract tests
    slow: Slow running tests
    asyncio: Async tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

#### Jest Configuration
```javascript
// jest.config.js
export default {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy'
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
    '!src/**/*.d.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  testMatch: [
    '<rootDir>/tests/**/*.test.{ts,tsx}'
  ],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'
  }
};
```

---

## API Development

### FastAPI Best Practices

#### Route Organization
```python
# src/api/routes/strategies.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import HTTPBearer
from typing import List, Optional
from pydantic import BaseModel, Field

from src.core.database_manager import DatabaseManager
from src.services.auth_service import AuthenticationService
from src.models.strategy import Strategy
from src.utils.validators import validate_strategy_parameters

router = APIRouter(prefix="/strategies", tags=["strategies"])
security = HTTPBearer()

class StrategyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    description: str = Field(..., min_length=1, max_length=500, description="Strategy description")
    category: str = Field(..., regex="^(predatory|quantitative|psychological|mathematical)$")
    risk_level: str = Field(..., regex="^(low|medium|high|extreme)$")
    parameters: dict = Field(..., description="Strategy parameters")
    is_active: bool = Field(default=False, description="Whether strategy is active")

class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    risk_level: str
    parameters: dict
    is_active: bool
    confidence_score: Optional[float] = None
    performance_metrics: Optional[dict] = None
    created_at: str
    updated_at: str

class StrategyListResponse(BaseModel):
    strategies: List[StrategyResponse]
    total: int
    limit: int
    offset: int

@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    category: Optional[str] = Query(None, regex="^(predatory|quantitative|psychological|mathematical)$"),
    risk_level: Optional[str] = Query(None, regex="^(low|medium|high|extreme)$"),
    active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of trading strategies with optional filtering.

    - **category**: Filter by strategy category
    - **risk_level**: Filter by risk level
    - **active**: Filter by active status
    - **limit**: Number of results per page (1-100)
    - **offset**: Offset for pagination
    """
    try:
        filters = {}
        if category:
            filters['category'] = category
        if risk_level:
            filters['risk_level'] = risk_level
        if active is not None:
            filters['is_active'] = active

        strategies, total = await db.list_strategies(
            filters=filters,
            limit=limit,
            offset=offset,
            user_id=current_user['id']
        )

        return StrategyListResponse(
            strategies=[StrategyResponse.from_orm(s) for s in strategies],
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    strategy_data: StrategyCreateRequest,
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new trading strategy.

    Validates strategy parameters and creates a new strategy instance.
    """
    try:
        # Validate strategy parameters
        validate_strategy_parameters(strategy_data.category, strategy_data.parameters)

        # Create strategy
        strategy = await db.create_strategy(
            name=strategy_data.name,
            description=strategy_data.description,
            category=strategy_data.category,
            risk_level=strategy_data.risk_level,
            parameters=strategy_data.parameters,
            is_active=strategy_data.is_active,
            user_id=current_user['id']
        )

        logger.info(f"Created strategy: {strategy.id} by user: {current_user['id']}")

        return StrategyResponse.from_orm(strategy)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str = Path(..., description="Strategy ID"),
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific strategy."""
    try:
        strategy = await db.get_strategy(strategy_id, user_id=current_user['id'])

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return StrategyResponse.from_orm(strategy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Dependency Injection
```python
# src/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from src.core.database_manager import DatabaseManager
from src.core.cache import CacheManager
from src.services.auth_service import AuthenticationService
from src.core.config import config

security = HTTPBearer()

async def get_database() -> DatabaseManager:
    """Get database manager instance"""
    db = DatabaseManager()
    try:
        yield db
    finally:
        await db.close()

async def get_cache() -> CacheManager:
    """Get cache manager instance"""
    cache = CacheManager()
    try:
        yield cache
    finally:
        await cache.close()

async def get_current_user(
    token: str = Depends(security),
    db: DatabaseManager = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
) -> dict:
    """Get current authenticated user"""
    try:
        # Verify JWT token
        payload = jwt.decode(
            token.credentials,
            config.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Check cache first
        user = await cache.get(f"user:{user_id}")
        if not user:
            # Get from database
            user = await db.get_user(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            # Cache user data
            await cache.set(f"user:{user_id}", user, expire=300)

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_live_trading_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get user with live trading permissions"""
    if not current_user.get('is_live_trading_enabled'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live trading not enabled for user"
        )
    return current_user
```

---

## Performance Guidelines

### Database Performance

#### Query Optimization
```python
# Efficient database queries
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload

class TradeRepository:
    async def get_user_trades_optimized(
        self,
        user_id: str,
        limit: int = 50,
        include_strategy: bool = True
    ) -> List[Trade]:
        """Optimized query for user trades with eager loading"""

        query = select(Trade).where(Trade.user_id == user_id)

        if include_strategy:
            # Use joinedload for one-to-one relationships
            query = query.options(joinedload(Trade.strategy))

        # Add pagination
        query = query.order_by(Trade.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().unique().all()

    async def get_portfolio_summary_efficient(self, user_id: str) -> dict:
        """Efficient portfolio summary using aggregations"""

        # Use database aggregations instead of Python calculations
        query = select(
            func.sum(case((Trade.side == 'buy', Trade.quantity), else_=-Trade.quantity)).label('total_quantity'),
            func.sum(Trade.quantity * Trade.executed_price).label('total_value'),
            func.count(Trade.id).label('total_trades'),
            func.avg(Trade.pnl_percent).label('avg_return')
        ).where(
            and_(
                Trade.user_id == user_id,
                Trade.status == 'executed'
            )
        )

        result = await self.session.execute(query)
        return result.first()._asdict()
```

#### Connection Pooling
```python
# src/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            # Connection pooling settings
            poolclass=QueuePool,
            pool_size=20,              # Number of persistent connections
            max_overflow=0,            # Don't create additional connections
            pool_pre_ping=True,        # Validate connections before use
            pool_recycle=3600,         # Recycle connections after 1 hour
            # Performance settings
            echo=False,                # Don't log SQL in production
            query_cache_size=1200,     # Cache prepared statements
        )

        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """Get database session with proper cleanup"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
```

### Caching Strategy

#### Redis Caching
```python
# src/core/cache.py
import json
import pickle
from typing import Any, Optional, Union
import redis.asyncio as redis

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(
            redis_url,
            max_connections=100,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic deserialization"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            # Try JSON first (for simple types)
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Fall back to pickle for complex objects
                return pickle.loads(value)

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
        serialize_method: str = 'json'
    ) -> bool:
        """Set value in cache with automatic serialization"""
        try:
            if serialize_method == 'json':
                serialized = json.dumps(value, default=str)
            else:
                serialized = pickle.dumps(value)

            await self.redis.set(key, serialized, ex=expire)
            return True

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def get_or_set(
        self,
        key: str,
        factory_func,
        expire: int = 3600
    ) -> Any:
        """Get from cache or set using factory function"""
        value = await self.get(key)
        if value is not None:
            return value

        # Generate value using factory function
        if asyncio.iscoroutinefunction(factory_func):
            value = await factory_func()
        else:
            value = factory_func()

        await self.set(key, value, expire)
        return value
```

#### Multi-Level Caching
```python
# src/utils/cache_decorator.py
import functools
from typing import Any, Callable, Optional
from src.core.cache import CacheManager

def cached(
    expire: int = 3600,
    key_prefix: str = "",
    use_memory_cache: bool = True
):
    """Multi-level caching decorator"""

    memory_cache = {}  # L1 cache (in-memory)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # L1 Cache (Memory) - fastest
            if use_memory_cache and cache_key in memory_cache:
                return memory_cache[cache_key]

            # L2 Cache (Redis) - fast
            cache_manager = CacheManager()
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                if use_memory_cache:
                    memory_cache[cache_key] = cached_result
                return cached_result

            # Cache miss - execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Store in caches
            await cache_manager.set(cache_key, result, expire)
            if use_memory_cache:
                memory_cache[cache_key] = result

            return result

        return wrapper
    return decorator

# Usage example
@cached(expire=300, key_prefix="market_data", use_memory_cache=True)
async def get_market_data(symbol: str) -> dict:
    """Get market data with multi-level caching"""
    # Expensive API call
    return await external_api.get_market_data(symbol)
```

### Async Programming Best Practices

#### Efficient Async Operations
```python
import asyncio
from typing import List, Dict, Any
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class MarketDataProcessor:
    def __init__(self):
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=20)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)

    async def fetch_multiple_symbols(self, symbols: List[str]) -> Dict[str, Any]:
        """Efficiently fetch data for multiple symbols concurrently"""

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(10)

        async def fetch_single_symbol(symbol: str) -> tuple:
            async with semaphore:
                try:
                    url = f"https://api.example.com/data/{symbol}"
                    async with self.session.get(url) as response:
                        data = await response.json()
                        return symbol, data
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
                    return symbol, None

        # Execute all requests concurrently
        tasks = [fetch_single_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        market_data = {}
        for result in results:
            if isinstance(result, tuple) and result[1] is not None:
                symbol, data = result
                market_data[symbol] = data

        return market_data

    async def process_heavy_calculation(self, data: List[dict]) -> List[dict]:
        """Offload CPU-intensive work to thread pool"""

        def calculate_indicators(item: dict) -> dict:
            # CPU-intensive calculation
            # This runs in a separate thread
            return perform_technical_analysis(item)

        # Process in batches to avoid overwhelming the thread pool
        batch_size = 100
        results = []

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]

            # Submit batch to thread pool
            tasks = [
                asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    calculate_indicators,
                    item
                )
                for item in batch
            ]

            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results
```

This comprehensive developer guide provides the foundation for building high-quality, maintainable code in the NIRAJ trading system. Follow these guidelines to ensure consistency, performance, and reliability across all components.
