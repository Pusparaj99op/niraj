# External API Testing Enhancement

## Overview
Enhanced `niraj.py` to include comprehensive testing for all external APIs integrated with the NIRAJ trading system.

## New Testing Capabilities

### 1. Broker APIs Testing 🏦
**Menu Option 3: Test Broker APIs (Angel One & Dhan)**

Tests integration with trading brokers:

#### Angel One API Tests:
- ✅ Market Data Status (`/api/angel-one/market-data/status`)
- ✅ Market Quotes (`/api/angel-one/market-data/quotes`)
- ✅ Last Traded Price (LTP) (`/api/angel-one/market-data/ltp`)
- ✅ Portfolio Data (`/api/angel-one/portfolio`)

**Supported Operations:**
- Historical data retrieval
- Trading (buy/sell orders)
- Real-time market feed
- News integration
- Portfolio management

#### Dhan API Tests:
- ✅ Market Data Status (`/api/dhan/market-data/status`)
- ✅ Market Quotes (`/api/dhan/market-data/quotes`)
- ✅ Last Traded Price (LTP) (`/api/dhan/market-data/ltp`)
- ✅ Portfolio Data (`/api/dhan/portfolio`)

**Supported Operations:**
- Historical data retrieval
- Real-time market feed
- Portfolio management

### 2. News API Testing 📰
**Menu Option 4: Test News APIs**

Tests news aggregation services:
- ✅ News Service Health (`/api/news/health`)
- ✅ Top Headlines (`/api/news/headlines`)
- ✅ Company-Specific News (`/api/news/company/AAPL`)

**Features:**
- Multiple news sources (NewsAPI, RSS feeds)
- Company-specific news filtering
- Market news aggregation

### 3. Weather API Testing 🌤️
**Menu Option 5: Test Weather APIs**

Tests weather data integration:
- ✅ Weather Service Health (`/api/weather/health`)
- ✅ Current Weather (`/api/weather/current`)
- ✅ Weather Forecast (`/api/weather/forecast`)

**Features:**
- Current weather conditions
- Multi-day forecasts
- Location-based weather data
- Integration with OpenWeatherMap

### 4. Comprehensive Testing 🔬
**Menu Option 6: Test All External APIs**

Runs complete test suite for all external APIs:
- Tests all broker endpoints (Angel One & Dhan)
- Tests all news endpoints
- Tests all weather endpoints
- Provides comprehensive summary with pass/fail counts

## Updated API Testing Menu

```
🧪 API Testing:
  1. 🔍 Test All API Endpoints (Core)
  2. 🏥 Quick Health Check
  3. 📡 Test Broker APIs (Angel One & Dhan)
  4. 📰 Test News APIs
  5. 🌤️  Test Weather APIs
  6. 🔬 Test All External APIs (Comprehensive)
  7. 📄 Test Specific Endpoint
  8. 📊 View API Documentation
  9. 🔄 Test WebSocket Connection
  0. ⬅️  Back to Main Menu
```

## Implementation Details

### New Methods Added to `NirajRunner` Class:

1. **`test_broker_apis()`** (Lines ~930-1035)
   - Tests Angel One and Dhan broker integrations
   - Validates market data, quotes, LTP, and portfolio endpoints
   - Displays results with detailed status codes and response data

2. **`test_news_api()`** (Lines ~1037-1090)
   - Tests news service health and headline retrieval
   - Validates company-specific news queries
   - Shows response data from news aggregators

3. **`test_weather_api()`** (Lines ~1092-1145)
   - Tests weather service health
   - Validates current weather and forecast endpoints
   - Displays weather data with conditions and temperatures

4. **`test_all_external_apis()`** (Lines ~1147-1200)
   - Comprehensive test runner for all external APIs
   - Aggregates results and displays summary
   - Shows total pass/fail counts across all services

### Menu Handler Updates:

Updated `MenuInterface.handle_api_testing()` (Line 2131) to route new menu choices:
- Choice 3 → `test_broker_apis()`
- Choice 4 → `test_news_api()`
- Choice 5 → `test_weather_api()`
- Choice 6 → `test_all_external_apis()`

## Usage Examples

### Test Broker APIs:
```bash
python niraj.py menu
# Select: 2 (API Testing & Documentation)
# Select: 3 (Test Broker APIs)
```

### Test All External APIs:
```bash
python niraj.py menu
# Select: 2 (API Testing & Documentation)
# Select: 6 (Test All External APIs)
```

### Quick Health Check (includes external APIs):
```bash
python niraj.py menu
# Select: 2 (API Testing & Documentation)
# Select: 2 (Quick Health Check)
```

## Broker-Specific Functionality

### Angel One Only:
- **Historical Data**: `/api/angel-one/market-data/historical`
- **Trading Operations**: `/api/angel-one/orders/place`, `/api/angel-one/orders/modify`
- **Market Feed**: `/api/angel-one/market-data/feed`
- **News Integration**: `/api/angel-one/news`
- **Portfolio**: `/api/angel-one/portfolio`

### Dhan Only:
- **Historical Data**: `/api/dhan/market-data/historical`
- **Market Feed**: `/api/dhan/market-data/feed`
- **Portfolio**: `/api/dhan/portfolio`

### Both Brokers:
- Market quotes and LTP
- Portfolio management
- Market data status

## Benefits

1. **Comprehensive Validation**: All external integrations tested systematically
2. **Broker-Specific Testing**: Separate tests for Angel One and Dhan capabilities
3. **Easy Debugging**: Detailed error messages and response data display
4. **Quick Status Checks**: Fast validation of all external services
5. **Integration Monitoring**: Regular health checks for third-party dependencies

## Technical Notes

- All tests use `requests` library for HTTP calls
- Default timeout: 10 seconds per request
- Results displayed with colored status indicators
- Error handling includes timeout and connection errors
- Test results show response times and data samples

## Next Steps

Consider adding:
1. **Performance metrics**: Track response times over multiple runs
2. **Historical test results**: Store test outcomes in database
3. **Automated alerts**: Notify on API failures
4. **Test scheduling**: Run tests at regular intervals
5. **Extended broker tests**: Add options trading, margin data, etc.

## Related Documentation

- `/home/pranay/Music/niraj/docs/API_REFERENCE.md` - Complete API documentation
- `/home/pranay/Music/niraj/backend/README.md` - Backend service details
- `/home/pranay/Music/niraj/NIRAJ_RUNNER_FIX.md` - Runner script enhancements
- `/home/pranay/Music/niraj/API_ROOT_ENDPOINT_FIX.md` - API root endpoint details
