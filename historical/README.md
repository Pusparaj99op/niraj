# Bank Nifty Historical Data

## Overview
This folder contains the maximum available historical data for Bank Nifty index downloaded from Yahoo Finance.

## Data Summary
- **Symbol**: BANKNIFTY
- **Ticker**: ^NSEBANK (Yahoo Finance)
- **Source**: Yahoo Finance (yfinance library)
- **Date Range**: September 17, 2007 to October 3, 2025
- **Data Span**: 18+ years
- **Total Records**: 4,152 trading days
- **Download Date**: October 5, 2025

## Data Statistics
- **Latest Close**: ₹55,589.25
- **All-time High**: ₹57,628.40
- **All-time Low**: ₹3,314.51
- **Average Volume**: 615,435
- **Mean Close**: ₹23,612.56
- **Best Daily Return**: +19.44%
- **Worst Daily Return**: -16.73%
- **Average Daily Return**: 0.067%

## Files Generated

### 1. CSV Format
**File**: `BANKNIFTY_historical_20251005_182113.csv`
- Size: ~507 KB
- Format: Comma-separated values
- Best for: Data analysis, Excel, spreadsheet applications
- Columns: Date, Open, High, Low, Close, Volume, Dividends, Stock Splits, Daily_Return

### 2. JSON Format
**File**: `BANKNIFTY_historical_20251005_182113.json`
- Size: ~1.2 MB
- Format: JavaScript Object Notation
- Best for: Programming, web applications, API integration
- Structure: Contains metadata and OHLCV data arrays

### 3. Summary Report
**File**: `BANKNIFTY_summary_20251005_182113.txt`
- Size: ~528 bytes
- Format: Plain text
- Contents: Quick reference summary of the dataset

## Data Columns

| Column | Description |
|--------|-------------|
| Date | Trading date with timezone (IST) |
| Open | Opening price of the day |
| High | Highest price of the day |
| Low | Lowest price of the day |
| Close | Closing price of the day |
| Volume | Trading volume |
| Dividends | Dividend payments (if any) |
| Stock Splits | Stock split events (if any) |
| Daily_Return | Daily percentage return |

## Usage Examples

### Python (pandas)
```python
import pandas as pd

# Load CSV data
df = pd.read_csv('historical/BANKNIFTY_historical_20251005_182113.csv')
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)

# Calculate moving averages
df['SMA_20'] = df['Close'].rolling(window=20).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()

# Analyze returns
monthly_returns = df['Daily_Return'].resample('M').sum()
```

### Python (JSON)
```python
import json

with open('historical/BANKNIFTY_historical_20251005_182113.json', 'r') as f:
    data = json.load(f)

print(f"Total records: {data['total_records']}")
print(f"Date range: {data['first_date']} to {data['last_date']}")

# Access OHLCV data
for record in data['data'][:5]:  # First 5 records
    print(f"{record['Date']}: Close = {record['Close']}")
```

### Excel/Spreadsheet
1. Open Excel or Google Sheets
2. Import the CSV file: `BANKNIFTY_historical_20251005_182113.csv`
3. The data will be automatically formatted with columns
4. Use pivot tables, charts, and formulas for analysis

## Backtesting Applications

This data can be used for:
- **Strategy Development**: Test trading strategies against historical data
- **Risk Analysis**: Calculate Value at Risk (VaR), drawdowns, volatility
- **Performance Metrics**: Sharpe ratio, Sortino ratio, maximum drawdown
- **Pattern Recognition**: Identify support/resistance levels, trend patterns
- **Statistical Analysis**: Correlation studies, regression analysis
- **Machine Learning**: Train predictive models for price forecasting

## Data Limitations

1. **Market Hours**: Data includes only regular trading session data
2. **Corporate Actions**: Some corporate actions may not be adjusted
3. **Holidays**: No data for market holidays and weekends
4. **Intraday Data**: This dataset contains daily (EOD) data only
5. **Gaps**: There may be gaps due to trading halts or data unavailability

## Updating Data

To download updated data, run:
```bash
python download_banknifty_yfinance.py
```

This will create new files with the latest timestamp.

## Alternative Data Sources

If you have broker API credentials, you can also use:
```bash
python download_banknifty_historical.py
```

This script supports:
- **Dhan**: Requires DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN
- **Angel One**: Requires Angel One API credentials

Set environment variables:
```bash
export DHAN_CLIENT_ID='your_client_id'
export DHAN_ACCESS_TOKEN='your_access_token'
```

## Data Quality Notes

✅ **Verified**:
- 18 years of continuous data
- No missing dates (except market holidays)
- All OHLCV fields populated
- Daily returns calculated

⚠️ **Notes**:
- Data is adjusted for splits and dividends by default
- Volume data may be 0 for some early dates (index characteristic)
- Timezone: IST (Indian Standard Time, UTC+5:30)

## Contact & Support

For issues or questions about this data:
1. Check the NIRAJ trading system documentation
2. Review the backend/src/api/dhan_client.py for API details
3. Consult Yahoo Finance documentation for data source questions

## License

This data is obtained from Yahoo Finance and is subject to their terms of service.
Use for personal/educational purposes in accordance with Yahoo Finance ToS.

---

**Generated**: October 5, 2025
**Script**: `download_banknifty_yfinance.py`
**NIRAJ Trading System** - Advanced Algorithmic Trading Platform
