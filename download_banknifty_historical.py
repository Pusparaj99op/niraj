"""
Download Maximum Historical Data for Bank Nifty
This script downloads all available historical data for Bank Nifty index
and stores it in the historical folder.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from src.api.dhan_client import DhanClient
    from src.core.config import config
    print("✓ Imported DhanClient successfully")
except ImportError as e:
    print(f"✗ Failed to import: {e}")
    print("Attempting alternative import...")
    try:
        from backend.src.api.dhan_client import DhanClient
        from backend.src.core.config import config
        print("✓ Imported DhanClient with alternative path")
    except ImportError as e2:
        print(f"✗ Failed alternative import: {e2}")
        sys.exit(1)


async def download_banknifty_historical():
    """Download maximum historical data for Bank Nifty"""
    
    print("\n" + "="*60)
    print("BANK NIFTY HISTORICAL DATA DOWNLOADER")
    print("="*60 + "\n")
    
    # Load configuration
    try:
        config.load_config()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"⚠ Warning loading config: {e}")
    
    # Get Dhan credentials from environment or config
    client_id = os.getenv('DHAN_CLIENT_ID') or config.get('brokers.dhan.client_id', '')
    access_token = os.getenv('DHAN_ACCESS_TOKEN') or config.get('brokers.dhan.access_token', '')
    
    if not client_id or not access_token:
        print("\n⚠ WARNING: Dhan credentials not found!")
        print("Please set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN environment variables")
        print("Or configure them in backend/config/development.yaml")
        print("\nUsing demo mode with mock data...\n")
        client_id = "DEMO_CLIENT"
        access_token = "DEMO_TOKEN"
    else:
        print(f"✓ Using Dhan Client ID: {client_id[:4]}****")
    
    # Initialize Dhan client
    try:
        dhan = DhanClient(client_id=client_id, access_token=access_token)
        print("✓ Dhan client initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize Dhan client: {e}")
        return
    
    # Bank Nifty parameters
    # Note: For index, we typically use the spot symbol
    symbol = "NIFTY BANK"  # Bank Nifty spot
    exchange_segment = "IDX_I"  # Index segment
    instrument_type = "INDEX"  # Index instrument
    security_id = "25"  # Bank Nifty security ID in Dhan
    
    print(f"Symbol: {symbol}")
    print(f"Exchange: {exchange_segment}")
    print(f"Instrument Type: {instrument_type}")
    print(f"Security ID: {security_id}\n")
    
    # Date range - Download maximum available history
    # Most brokers provide 5-10 years of historical data
    # Dhan typically provides up to 10 years for indices
    
    to_date = datetime.now()
    # Try to get 10 years of data
    from_date = to_date - timedelta(days=365 * 10)
    
    print(f"Date Range:")
    print(f"  From: {from_date.strftime('%Y-%m-%d')}")
    print(f"  To:   {to_date.strftime('%Y-%m-%d')}")
    print(f"  Duration: ~10 years\n")
    
    # Create historical directory
    historical_dir = Path("historical")
    historical_dir.mkdir(exist_ok=True)
    print(f"✓ Historical directory: {historical_dir.absolute()}\n")
    
    print("Downloading historical data...")
    print("This may take a few minutes...\n")
    
    try:
        # Download daily historical data
        historical_data = await dhan.get_historical_daily_data(
            symbol=symbol,
            exchange_segment=exchange_segment,
            instrument_type=instrument_type,
            from_date=from_date.strftime('%Y-%m-%d'),
            to_date=to_date.strftime('%Y-%m-%d'),
            expiry_code=0  # Not needed for index
        )
        
        print("✓ Data downloaded successfully!\n")
        
        # Display data summary
        if historical_data and 'data' in historical_data:
            data = historical_data['data']
            num_candles = len(data.get('open', []))
            
            print("="*60)
            print("DATA SUMMARY")
            print("="*60)
            print(f"Total candles: {num_candles}")
            
            if num_candles > 0:
                start_times = data.get('start_Time', [])
                if start_times:
                    print(f"First date: {start_times[0] if isinstance(start_times[0], str) else datetime.fromtimestamp(start_times[0]).strftime('%Y-%m-%d')}")
                    print(f"Last date: {start_times[-1] if isinstance(start_times[-1], str) else datetime.fromtimestamp(start_times[-1]).strftime('%Y-%m-%d')}")
                
                opens = data.get('open', [])
                highs = data.get('high', [])
                lows = data.get('low', [])
                closes = data.get('close', [])
                volumes = data.get('volume', [])
                
                if closes:
                    print(f"\nLatest Close: {closes[-1]:.2f}")
                    print(f"Highest: {max(highs):.2f}")
                    print(f"Lowest: {min(lows):.2f}")
                
                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    print(f"Average Volume: {avg_volume:,.0f}")
            
            print("="*60 + "\n")
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"BANKNIFTY_historical_{timestamp}.json"
        filepath = historical_dir / filename
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        print(f"✓ Data saved to: {filepath}")
        print(f"  File size: {filepath.stat().st_size / 1024:.2f} KB\n")
        
        # Also save as CSV for easy analysis
        csv_filename = f"BANKNIFTY_historical_{timestamp}.csv"
        csv_filepath = historical_dir / csv_filename
        
        if historical_data and 'data' in historical_data:
            data = historical_data['data']
            import csv
            
            with open(csv_filepath, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                num_rows = len(data.get('open', []))
                for i in range(num_rows):
                    timestamp = data.get('start_Time', [])[i]
                    if isinstance(timestamp, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    writer.writerow({
                        'timestamp': timestamp,
                        'open': data.get('open', [])[i],
                        'high': data.get('high', [])[i],
                        'low': data.get('low', [])[i],
                        'close': data.get('close', [])[i],
                        'volume': data.get('volume', [])[i]
                    })
            
            print(f"✓ CSV saved to: {csv_filepath}")
            print(f"  File size: {csv_filepath.stat().st_size / 1024:.2f} KB\n")
        
        print("="*60)
        print("✓ DOWNLOAD COMPLETE!")
        print("="*60)
        print("\nFiles saved in 'historical' folder:")
        print(f"  - {filename} (JSON format)")
        print(f"  - {csv_filename} (CSV format)")
        print("\nYou can now use this data for backtesting and analysis.")
        
    except Exception as e:
        print(f"\n✗ Error downloading data: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # If it's an authentication error, provide guidance
        if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
            print("\n⚠ Authentication Error!")
            print("Please check your Dhan credentials:")
            print("  1. Get your Client ID and Access Token from Dhan")
            print("  2. Set environment variables:")
            print("     export DHAN_CLIENT_ID='your_client_id'")
            print("     export DHAN_ACCESS_TOKEN='your_access_token'")
        
        import traceback
        print("\nFull error traceback:")
        traceback.print_exc()
    
    finally:
        # Close the client
        try:
            await dhan.close()
            print("\n✓ Dhan client closed")
        except Exception as e:
            print(f"\n⚠ Warning closing client: {e}")


def main():
    """Main entry point"""
    try:
        asyncio.run(download_banknifty_historical())
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
