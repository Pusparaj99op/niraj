# Bank Stocks Historical Data

## Overview
This folder contains comprehensive historical data for 20 major Indian bank stocks, covering both public and private sector banks.

## Data Summary
- **Total Banks**: 20 (9 Public Sector + 11 Private Sector)
- **Timeframes**: 
  - Daily (1D): Maximum available history (10-20+ years)
  - Intraday (15-min): Last 60 days
- **Source**: Yahoo Finance via yfinance
- **Update Method**: Intelligent merge (preserves old data, adds new)

## Bank List

### Public Sector Banks (9)
1. **SBI** - State Bank of India
2. **PNB** - Punjab National Bank
3. **BANKBARODA** - Bank of Baroda
4. **CANBK** - Canara Bank
5. **UNIONBANK** - Union Bank of India
6. **INDIANB** - Indian Bank
7. **IOB** - Indian Overseas Bank
8. **CENTRALBK** - Central Bank of India
9. **MAHABANK** - Bank of Maharashtra

### Private Sector Banks (11)
1. **HDFCBANK** - HDFC Bank
2. **ICICIBANK** - ICICI Bank
3. **AXISBANK** - Axis Bank
4. **KOTAKBANK** - Kotak Mahindra Bank
5. **INDUSINDBK** - IndusInd Bank
6. **FEDERALBNK** - Federal Bank
7. **BANDHANBNK** - Bandhan Bank
8. **IDFCFIRSTB** - IDFC First Bank
9. **RBLBANK** - RBL Bank
10. **YESBANK** - Yes Bank
11. **AUBANK** - AU Small Finance Bank

## Folder Structure

```
historical/
├── SYMBOL/                    (e.g., HDFCBANK, SBI, etc.)
│   ├── daily/
│   │   └── SYMBOL_daily.csv   (Daily OHLCV data)
│   └── 15min/
│       └── SYMBOL_15min.csv   (15-minute intraday data)
├── BANKNIFTY_*.csv            (Bank Nifty index data)
├── BANKS_SUMMARY.txt          (Download summary)
└── BANKS_DATA_README.md       (This file)
```

## Data Columns

### Daily Data (SYMBOL_daily.csv)
| Column | Description |
|--------|-------------|
| Date | Trading date (index) |
| Open | Opening price |
| High | Highest price of the day |
| Low | Lowest price of the day |
| Close | Closing price |
| Volume | Trading volume |
| Dividends | Dividend payments |
| Stock Splits | Stock split events |

### 15-Minute Data (SYMBOL_15min.csv)
| Column | Description |
|--------|-------------|
| Datetime | Date and time (index) |
| Open | Opening price for 15-min candle |
| High | Highest price in 15-min |
| Low | Lowest price in 15-min |
| Close | Closing price |
| Volume | Trading volume |
| Dividends | Dividend payments |
| Stock Splits | Stock split events |

## Usage

### Download New Data
```bash
# Initial download (creates new files)
python download_all_banks_historical.py
```

### Update Existing Data
```bash
# Update mode (merges with existing data)
python download_all_banks_historical.py --update
```

### Using NIRAJ Menu
1. Run: `python niraj.py`
2. Select option **18** to download
3. Select option **19** to update

## Python Usage Examples

### Load Daily Data
```python
import pandas as pd

# Load HDFC Bank daily data
df = pd.read_csv('historical/HDFCBANK/daily/HDFCBANK_daily.csv', 
                 index_col=0, parse_dates=True)

print(f"Total records: {len(df)}")
print(f"Date range: {df.index[0]} to {df.index[-1]}")
print(df.tail())
```

### Load 15-Minute Data
```python
import pandas as pd

# Load SBI intraday data
df_15m = pd.read_csv('historical/SBI/15min/SBI_15min.csv',
                     index_col=0, parse_dates=True)

print(f"15-min candles: {len(df_15m)}")
print(df_15m.head())
```

### Compare Multiple Banks
```python
import pandas as pd
import matplotlib.pyplot as plt

banks = ['HDFCBANK', 'ICICIBANK', 'AXISBANK', 'SBIN']
data = {}

for bank in banks:
    file_path = f'historical/{bank}/daily/{bank}_daily.csv'
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    data[bank] = df['Close']

# Combine into single DataFrame
combined = pd.DataFrame(data)

# Normalize to 100 for comparison
normalized = combined / combined.iloc[0] * 100

# Plot
normalized.plot(figsize=(12, 6), title='Bank Stocks Performance Comparison')
plt.ylabel('Normalized Price (Base 100)')
plt.xlabel('Date')
plt.legend()
plt.grid(True)
plt.show()
```

### Calculate Technical Indicators
```python
import pandas as pd

# Load data
df = pd.read_csv('historical/HDFCBANK/daily/HDFCBANK_daily.csv',
                 index_col=0, parse_dates=True)

# Moving Averages
df['SMA_20'] = df['Close'].rolling(window=20).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()
df['SMA_200'] = df['Close'].rolling(window=200).mean()

# RSI
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# Bollinger Bands
df['BB_Middle'] = df['Close'].rolling(window=20).mean()
df['BB_Std'] = df['Close'].rolling(window=20).std()
df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)

print(df[['Close', 'SMA_20', 'SMA_50', 'RSI', 'BB_Upper', 'BB_Lower']].tail())
```

### Backtesting Strategy Example
```python
import pandas as pd

# Load data
df = pd.read_csv('historical/SBIN/daily/SBI_daily.csv',
                 index_col=0, parse_dates=True)

# Simple SMA Crossover Strategy
df['SMA_20'] = df['Close'].rolling(window=20).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()

# Generate signals
df['Signal'] = 0
df.loc[df['SMA_20'] > df['SMA_50'], 'Signal'] = 1
df.loc[df['SMA_20'] < df['SMA_50'], 'Signal'] = -1

# Calculate returns
df['Daily_Return'] = df['Close'].pct_change()
df['Strategy_Return'] = df['Signal'].shift(1) * df['Daily_Return']

# Performance metrics
total_return = (1 + df['Strategy_Return']).prod() - 1
sharpe_ratio = df['Strategy_Return'].mean() / df['Strategy_Return'].std() * (252**0.5)

print(f"Total Return: {total_return*100:.2f}%")
print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
```

## Data Quality

### Verified
- ✅ Maximum available history downloaded
- ✅ No missing trading days (except holidays)
- ✅ All OHLCV fields populated
- ✅ Data adjusted for splits and dividends
- ✅ Timezone: IST (UTC+5:30)

### Limitations
1. **15-Minute Data**: Limited to last 60 days (Yahoo Finance limitation)
2. **Market Hours**: Only regular trading session data
3. **Holidays**: No data for market holidays and weekends
4. **Pre/Post Market**: No pre-market or after-hours data

## Update Schedule

### Recommended Update Frequency
- **Daily Data**: Once per week (Friday after market close)
- **15-Min Data**: Daily (to maintain rolling 60-day window)

### Automated Updates
You can set up a cron job for automated updates:

```bash
# Add to crontab (crontab -e)
# Update every Friday at 6 PM
0 18 * * 5 cd /path/to/niraj && python download_all_banks_historical.py --update

# Or daily at 6 PM for intraday data
0 18 * * * cd /path/to/niraj && python download_all_banks_historical.py --update
```

## File Sizes

Approximate file sizes per bank:
- **Daily CSV**: 200-800 KB (depends on history length)
- **15-Min CSV**: 100-150 KB (60 days)

Total folder size: ~50-70 MB for all 20 banks

## Integration with NIRAJ

### Backend API
Data can be loaded into the NIRAJ backend for:
- Strategy backtesting
- Live trading decisions
- AI model training
- Portfolio analysis

### Database Import
```python
import sqlite3
import pandas as pd
from pathlib import Path

conn = sqlite3.connect('backend/data/niraj.db')

# Import all banks
historical_path = Path('historical')
for bank_dir in historical_path.iterdir():
    if bank_dir.is_dir() and bank_dir.name.isupper():
        symbol = bank_dir.name
        
        # Import daily data
        daily_csv = bank_dir / 'daily' / f'{symbol}_daily.csv'
        if daily_csv.exists():
            df = pd.read_csv(daily_csv)
            df['symbol'] = symbol
            df.to_sql(f'{symbol}_daily', conn, if_exists='replace', index=False)
        
        # Import 15-min data
        intraday_csv = bank_dir / '15min' / f'{symbol}_15min.csv'
        if intraday_csv.exists():
            df = pd.read_csv(intraday_csv)
            df['symbol'] = symbol
            df.to_sql(f'{symbol}_15min', conn, if_exists='replace', index=False)

conn.close()
print("✅ All bank data imported to database")
```

## Troubleshooting

### Issue: Download fails
**Solution**: Check internet connection, verify yfinance is installed
```bash
pip install --upgrade yfinance
```

### Issue: Update shows +0 new records
**Reason**: No new trading data since last download (expected on weekends/holidays)

### Issue: Missing data for specific bank
**Solution**: Some banks may have limited history or API issues. Try downloading again.

### Issue: File permission errors
**Solution**: Ensure you have write permissions:
```bash
chmod -R u+w historical/
```

## Best Practices

1. **Regular Backups**: Backup the historical folder periodically
2. **Version Control**: Consider adding large CSVs to .gitignore
3. **Data Validation**: Verify data integrity after updates
4. **Compression**: Zip old data to save space
5. **Documentation**: Keep track of when data was last updated

## Data Sources & Attribution

- **Provider**: Yahoo Finance
- **Library**: yfinance (Python)
- **License**: Subject to Yahoo Finance Terms of Service
- **Usage**: Personal, educational, research purposes

## Support

For issues or questions:
1. Check NIRAJ documentation: `docs/`
2. Review script: `download_all_banks_historical.py`
3. Check logs for errors
4. Ensure yfinance is up to date

## Changelog

### 2025-10-05 - Initial Release
- ✅ Downloaded data for 20 major banks
- ✅ Both daily and 15-min timeframes
- ✅ Organized folder structure
- ✅ Update functionality implemented
- ✅ Integrated with NIRAJ menu

---

**Last Updated**: 2025-10-05
**NIRAJ Advanced Trading System**
**Data Management Module**
