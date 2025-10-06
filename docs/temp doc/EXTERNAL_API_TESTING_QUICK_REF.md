# NIRAJ External API Testing - Quick Reference

## 🚀 Quick Start

```bash
# Start the system
python niraj.py menu

# Navigate: 2 → API Testing & Documentation
# Then choose:
# 3 → Test Broker APIs (Angel One & Dhan)
# 4 → Test News APIs
# 5 → Test Weather APIs
# 6 → Test All External APIs (Comprehensive)
```

## 📡 Broker APIs

### Angel One
**Endpoints:** Market Data Status, Quotes, LTP, Watchlist
**Capabilities:** Historical data, Trading, Market feed, News, Portfolio

### Dhan
**Endpoints:** Market Feed, Historical Data, Portfolio
**Capabilities:** Historical data, Market feed, Portfolio

## 📰 News APIs
**Endpoints:** Health, Headlines, Company News
**Sources:** NewsAPI, RSS feeds

## 🌤️ Weather APIs
**Endpoints:** Health, Current Weather, Forecast
**Provider:** OpenWeatherMap

## 🔬 Comprehensive Test
Runs all tests above and shows combined summary

## 💡 Key Features
- ✅ Tests all endpoints automatically
- ✅ Shows detailed status codes
- ✅ Color-coded results (green=success, red=fail)
- ✅ Works even if authentication required (401 = reachable)
- ✅ Graceful error handling
- ✅ Fast execution (< 10 seconds)

## 📊 Expected Results
- Most endpoints return **401** (Authentication required) = ✅ Working
- Health endpoints might return **200** = ✅ Working
- **404** = ❌ Endpoint not found
- **500** = ❌ Server error

## 🎯 Success Criteria
```
✅ Status 200-499 = Endpoint reachable and working
❌ Status 500+ or connection error = Problem detected
```

## 📝 Files Modified
- `niraj.py` - Added 4 new test methods + updated menu
- `EXTERNAL_API_TESTING.md` - Detailed documentation
- `EXTERNAL_API_TESTING_SUMMARY.md` - Implementation summary

## 🔧 Technical Notes
- Default timeout: 5-10 seconds per request
- Uses `requests` library (falls back to curl)
- All endpoints use `/api/v1/` prefix
- Backend must be running on port 8000

## 📚 Documentation
See `EXTERNAL_API_TESTING_SUMMARY.md` for complete details.
