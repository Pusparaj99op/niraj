"""
Download Historical Data for All Major Bank Stocks
Supports both daily and 15-minute timeframes
Organizes data in separate folders per bank
Updates existing files instead of creating new ones
"""

import os
import sys
from datetime import datetime, timedelta
import json
from pathlib import Path
import pandas as pd

print("\n" + "="*70)
print("BANK STOCKS HISTORICAL DATA DOWNLOADER")
print("Daily & 15-Minute Timeframes")
print("="*70 + "\n")

# Check if yfinance is installed
try:
    import yfinance as yf
    print("✓ yfinance library found")
except ImportError:
    print("✗ yfinance not installed. Installing...")
    os.system("pip install yfinance")
    import yfinance as yf
    print("✓ yfinance installed successfully")

# Major Indian Bank Stocks (NSE)
BANK_STOCKS = {
    # Public Sector Banks
    "SBI": {"name": "State Bank of India", "ticker": "SBIN.NS"},
    "PNB": {"name": "Punjab National Bank", "ticker": "PNB.NS"},
    "BANKBARODA": {"name": "Bank of Baroda", "ticker": "BANKBARODA.NS"},
    "CANBK": {"name": "Canara Bank", "ticker": "CANBK.NS"},
    "UNIONBANK": {"name": "Union Bank of India", "ticker": "UNIONBANK.NS"},
    "INDIANB": {"name": "Indian Bank", "ticker": "INDIANB.NS"},
    "IOB": {"name": "Indian Overseas Bank", "ticker": "IOB.NS"},
    "CENTRALBK": {"name": "Central Bank of India", "ticker": "CENTRALBK.NS"},
    "MAHABANK": {"name": "Bank of Maharashtra", "ticker": "MAHABANK.NS"},
    
    # Private Sector Banks
    "HDFCBANK": {"name": "HDFC Bank", "ticker": "HDFCBANK.NS"},
    "ICICIBANK": {"name": "ICICI Bank", "ticker": "ICICIBANK.NS"},
    "AXISBANK": {"name": "Axis Bank", "ticker": "AXISBANK.NS"},
    "KOTAKBANK": {"name": "Kotak Mahindra Bank", "ticker": "KOTAKBANK.NS"},
    "INDUSINDBK": {"name": "IndusInd Bank", "ticker": "INDUSINDBK.NS"},
    "FEDERALBNK": {"name": "Federal Bank", "ticker": "FEDERALBNK.NS"},
    "BANDHANBNK": {"name": "Bandhan Bank", "ticker": "BANDHANBNK.NS"},
    "IDFCFIRSTB": {"name": "IDFC First Bank", "ticker": "IDFCFIRSTB.NS"},
    "RBLBANK": {"name": "RBL Bank", "ticker": "RBLBANK.NS"},
    "YESBANK": {"name": "Yes Bank", "ticker": "YESBANK.NS"},
    "AUBANK": {"name": "AU Small Finance Bank", "ticker": "AUBANK.NS"},
}


def create_folder_structure(base_dir="historical"):
    """Create organized folder structure for bank data"""
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)
    
    # Create folders for each bank
    for symbol in BANK_STOCKS.keys():
        bank_dir = base_path / symbol
        bank_dir.mkdir(exist_ok=True)
        
        # Create subfolders for timeframes
        (bank_dir / "daily").mkdir(exist_ok=True)
        (bank_dir / "15min").mkdir(exist_ok=True)
    
    print(f"✓ Folder structure created in {base_path.absolute()}")
    return base_path


def download_daily_data(symbol, ticker, base_path, update_mode=False):
    """Download daily historical data"""
    print(f"\n  📊 Daily data for {symbol} ({BANK_STOCKS[symbol]['name']})...")
    
    try:
        # Download max available data
        stock = yf.Ticker(ticker)
        df = stock.history(period="max")
        
        if df.empty:
            print(f"    ✗ No data available")
            return False
        
        # File path
        file_path = base_path / symbol / "daily" / f"{symbol}_daily.csv"
        
        if update_mode and file_path.exists():
            # Update existing file
            existing_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            # Merge: keep old data and add only new data
            combined = pd.concat([existing_df, df])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
            
            # Save updated data
            combined.to_csv(file_path)
            
            new_records = len(combined) - len(existing_df)
            print(f"    ✓ Updated: {len(combined)} total records (+{new_records} new)")
        else:
            # Save new file
            df.to_csv(file_path)
            print(f"    ✓ Saved: {len(df)} records")
            print(f"      From: {df.index[0].strftime('%Y-%m-%d')}")
            print(f"      To:   {df.index[-1].strftime('%Y-%m-%d')}")
        
        return True
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def download_intraday_data(symbol, ticker, base_path, update_mode=False):
    """Download 15-minute intraday data (last 60 days max from Yahoo)"""
    print(f"  ⏱️  15-min data for {symbol}...")
    
    try:
        # Yahoo Finance provides intraday for limited period
        stock = yf.Ticker(ticker)
        df = stock.history(period="60d", interval="15m")
        
        if df.empty:
            print(f"    ✗ No intraday data available")
            return False
        
        # File path
        file_path = base_path / symbol / "15min" / f"{symbol}_15min.csv"
        
        if update_mode and file_path.exists():
            # Update existing file
            existing_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            # Merge and remove duplicates
            combined = pd.concat([existing_df, df])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined.sort_index(inplace=True)
            
            # Save updated data
            combined.to_csv(file_path)
            
            new_records = len(combined) - len(existing_df)
            print(f"    ✓ Updated: {len(combined)} total records (+{new_records} new)")
        else:
            # Save new file
            df.to_csv(file_path)
            print(f"    ✓ Saved: {len(df)} records (last 60 days)")
        
        return True
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False


def download_all_banks(update_mode=False):
    """Download data for all banks"""
    
    mode_str = "UPDATE" if update_mode else "DOWNLOAD"
    print(f"\n{'='*70}")
    print(f"Starting {mode_str} for {len(BANK_STOCKS)} banks...")
    print(f"{'='*70}\n")
    
    # Create folder structure
    base_path = create_folder_structure()
    
    # Statistics
    stats = {
        "daily_success": 0,
        "daily_failed": 0,
        "intraday_success": 0,
        "intraday_failed": 0,
    }
    
    # Download data for each bank
    for i, (symbol, info) in enumerate(BANK_STOCKS.items(), 1):
        print(f"\n[{i}/{len(BANK_STOCKS)}] {info['name']} ({symbol})")
        print("-" * 70)
        
        # Daily data
        if download_daily_data(symbol, info['ticker'], base_path, update_mode):
            stats["daily_success"] += 1
        else:
            stats["daily_failed"] += 1
        
        # 15-minute data
        if download_intraday_data(symbol, info['ticker'], base_path, update_mode):
            stats["intraday_success"] += 1
        else:
            stats["intraday_failed"] += 1
    
    # Summary
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"Daily Data:     {stats['daily_success']}/{len(BANK_STOCKS)} successful")
    print(f"15-Min Data:    {stats['intraday_success']}/{len(BANK_STOCKS)} successful")
    print(f"Total Success:  {stats['daily_success'] + stats['intraday_success']}")
    print(f"Total Failed:   {stats['daily_failed'] + stats['intraday_failed']}")
    print("="*70 + "\n")
    
    # Create summary file
    create_summary_file(base_path, stats, update_mode)
    
    return stats


def create_summary_file(base_path, stats, update_mode):
    """Create a summary file with download information"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mode_str = "Updated" if update_mode else "Downloaded"
    
    summary = f"""
{"="*70}
BANK STOCKS HISTORICAL DATA SUMMARY
{"="*70}

{mode_str} Date: {timestamp}
Total Banks: {len(BANK_STOCKS)}

Data Timeframes:
  • Daily: Maximum available history
  • 15-Min: Last 60 days (Yahoo Finance limitation)

Download Statistics:
  Daily Data Success:    {stats['daily_success']}/{len(BANK_STOCKS)}
  15-Min Data Success:   {stats['intraday_success']}/{len(BANK_STOCKS)}
  Total Success:         {stats['daily_success'] + stats['intraday_success']}
  Total Failed:          {stats['daily_failed'] + stats['intraday_failed']}

Bank List:
"""
    
    for symbol, info in BANK_STOCKS.items():
        summary += f"  • {symbol:15s} - {info['name']}\n"
    
    summary += f"\n{'='*70}\n"
    summary += "Folder Structure:\n"
    summary += "  historical/\n"
    summary += "    ├── SYMBOL/\n"
    summary += "    │   ├── daily/\n"
    summary += "    │   │   └── SYMBOL_daily.csv\n"
    summary += "    │   └── 15min/\n"
    summary += "    │       └── SYMBOL_15min.csv\n"
    summary += f"{'='*70}\n"
    
    # Save summary
    summary_file = base_path / "BANKS_SUMMARY.txt"
    with open(summary_file, 'w') as f:
        f.write(summary)
    
    print(f"✓ Summary saved to: {summary_file}")


def main():
    """Main entry point"""
    import sys
    
    # Check for update mode
    update_mode = False
    if len(sys.argv) > 1 and sys.argv[1] in ['--update', '-u', 'update']:
        update_mode = True
        print("🔄 UPDATE MODE: Will update existing files")
    else:
        print("📥 DOWNLOAD MODE: Will create new files")
    
    try:
        stats = download_all_banks(update_mode)
        
        print("\n✅ Process completed successfully!")
        print(f"\nData stored in: ./historical/")
        print("\nTo update existing data in the future, run:")
        print("  python download_all_banks_historical.py --update")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
