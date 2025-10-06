"""
Download Maximum Historical Data for Bank Nifty using Yahoo Finance
This script downloads all available historical data for Bank Nifty index
using yfinance (no API credentials required)
"""

import sys
import os
from datetime import datetime, timedelta
import json
from pathlib import Path

print("\n" + "="*60)
print("BANK NIFTY HISTORICAL DATA DOWNLOADER")
print("Using Yahoo Finance (No API credentials required)")
print("="*60 + "\n")

# Check if yfinance is installed
try:
    import yfinance as yf
    print("✓ yfinance library found")
except ImportError:
    print("✗ yfinance not installed. Installing...")
    os.system("pip install yfinance")
    import yfinance as yf
    print("✓ yfinance installed successfully")

import pandas as pd

def download_banknifty_historical():
    """Download maximum historical data for Bank Nifty"""
    
    # Bank Nifty ticker symbol on Yahoo Finance
    ticker = "^NSEBANK"  # Bank Nifty Index
    
    print(f"\nTicker Symbol: {ticker}")
    print(f"Index: Bank Nifty (NSE)")
    
    # Date range - Get maximum available history
    # Yahoo Finance typically provides 10+ years of data
    to_date = datetime.now()
    from_date = datetime(2000, 1, 1)  # Start from 2000, yfinance will give max available
    
    print(f"\nRequesting data from: {from_date.strftime('%Y-%m-%d')}")
    print(f"                  to: {to_date.strftime('%Y-%m-%d')}")
    print("(Yahoo Finance will provide maximum available history)\n")
    
    # Create historical directory
    historical_dir = Path("historical")
    historical_dir.mkdir(exist_ok=True)
    print(f"✓ Historical directory: {historical_dir.absolute()}\n")
    
    print("Downloading historical data from Yahoo Finance...")
    print("This may take a minute...\n")
    
    try:
        # Download data
        bank_nifty = yf.Ticker(ticker)
        
        # Get maximum available historical data
        df = bank_nifty.history(period="max")
        
        if df.empty:
            print("✗ No data received. Trying alternative method...")
            # Try with explicit date range
            df = yf.download(ticker, start=from_date, end=to_date, progress=False)
        
        if df.empty:
            print("✗ No data available for Bank Nifty")
            return
        
        print("✓ Data downloaded successfully!\n")
        
        # Display data summary
        print("="*60)
        print("DATA SUMMARY")
        print("="*60)
        print(f"Total trading days: {len(df)}")
        print(f"First date: {df.index[0].strftime('%Y-%m-%d')}")
        print(f"Last date: {df.index[-1].strftime('%Y-%m-%d')}")
        
        years = (df.index[-1] - df.index[0]).days / 365.25
        print(f"Data span: {years:.1f} years")
        
        print(f"\nLatest Close: {df['Close'].iloc[-1]:.2f}")
        print(f"Highest (all-time): {df['High'].max():.2f}")
        print(f"Lowest (all-time): {df['Low'].min():.2f}")
        print(f"Average Volume: {df['Volume'].mean():,.0f}")
        
        # Additional statistics
        print(f"\nPrice Statistics:")
        print(f"  Mean Close: {df['Close'].mean():.2f}")
        print(f"  Median Close: {df['Close'].median():.2f}")
        print(f"  Std Dev: {df['Close'].std():.2f}")
        
        # Calculate returns
        df['Daily_Return'] = df['Close'].pct_change() * 100
        print(f"\nDaily Returns:")
        print(f"  Average: {df['Daily_Return'].mean():.3f}%")
        print(f"  Best day: {df['Daily_Return'].max():.2f}%")
        print(f"  Worst day: {df['Daily_Return'].min():.2f}%")
        
        print("="*60 + "\n")
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"BANKNIFTY_historical_{timestamp}.csv"
        csv_filepath = historical_dir / csv_filename
        
        df.to_csv(csv_filepath)
        print(f"✓ CSV saved to: {csv_filepath}")
        print(f"  File size: {csv_filepath.stat().st_size / 1024:.2f} KB")
        
        # Save to JSON
        json_filename = f"BANKNIFTY_historical_{timestamp}.json"
        json_filepath = historical_dir / json_filename
        
        # Convert to JSON-friendly format
        json_data = {
            'symbol': 'BANKNIFTY',
            'ticker': ticker,
            'download_date': datetime.now().isoformat(),
            'first_date': df.index[0].isoformat(),
            'last_date': df.index[-1].isoformat(),
            'total_records': len(df),
            'data': df.reset_index().to_dict(orient='records')
        }
        
        with open(json_filepath, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        print(f"✓ JSON saved to: {json_filepath}")
        print(f"  File size: {json_filepath.stat().st_size / 1024:.2f} KB\n")
        
        # Save to Excel for easy viewing
        try:
            excel_filename = f"BANKNIFTY_historical_{timestamp}.xlsx"
            excel_filepath = historical_dir / excel_filename
            df.to_excel(excel_filepath)
            print(f"✓ Excel saved to: {excel_filepath}")
            print(f"  File size: {excel_filepath.stat().st_size / 1024:.2f} KB\n")
        except Exception as e:
            print(f"⚠ Excel export skipped (openpyxl not installed): {e}\n")
        
        # Create a summary file
        summary_filename = f"BANKNIFTY_summary_{timestamp}.txt"
        summary_filepath = historical_dir / summary_filename
        
        with open(summary_filepath, 'w') as f:
            f.write("="*60 + "\n")
            f.write("BANK NIFTY HISTORICAL DATA SUMMARY\n")
            f.write("="*60 + "\n\n")
            f.write(f"Download Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Symbol: BANKNIFTY\n")
            f.write(f"Ticker: {ticker}\n")
            f.write(f"Source: Yahoo Finance\n\n")
            f.write(f"Total Records: {len(df)}\n")
            f.write(f"Date Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}\n")
            f.write(f"Data Span: {years:.1f} years\n\n")
            f.write("Files Generated:\n")
            f.write(f"  - {csv_filename} (CSV format)\n")
            f.write(f"  - {json_filename} (JSON format)\n")
            if excel_filepath.exists():
                f.write(f"  - {excel_filename} (Excel format)\n")
            f.write("\n" + "="*60 + "\n")
        
        print(f"✓ Summary saved to: {summary_filepath}\n")
        
        print("="*60)
        print("✓ DOWNLOAD COMPLETE!")
        print("="*60)
        print("\nAll files saved in 'historical' folder:")
        print(f"  • {csv_filename} - CSV format (for analysis)")
        print(f"  • {json_filename} - JSON format (for programming)")
        if excel_filepath.exists():
            print(f"  • {excel_filename} - Excel format (for viewing)")
        print(f"  • {summary_filename} - Summary report")
        print("\n✓ You can now use this data for backtesting and analysis!")
        print("\nData columns available:")
        print(f"  {', '.join(df.columns.tolist())}")
        
    except Exception as e:
        print(f"\n✗ Error downloading data: {e}")
        print(f"Error type: {type(e).__name__}")
        
        import traceback
        print("\nFull error traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        download_banknifty_historical()
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
