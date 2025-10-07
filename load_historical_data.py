"""
Load Historical Bank Data into NIRAJ Database

This script loads CSV historical data into the SQLite database
for the NIRAJ trading system backend.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import structlog

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

logger = structlog.get_logger()


# Define DataSourceType locally
YAHOO_FINANCE = "yahoo_finance"


print("\n" + "=" * 70)
print("LOAD HISTORICAL BANK DATA INTO DATABASE")
print("=" * 70 + "\n")


def parse_csv_date(date_str: str) -> datetime:
    """Parse date string from CSV"""
    # Handle timezone info
    if '+05:30' in date_str:
        # Remove timezone for now, assume IST
        date_str = date_str.replace('+05:30', '').strip()

    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {date_str}")


def load_csv_file(csv_path: Path, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
    """Load data from a single CSV file"""

    print(f"  📊 Loading {symbol} {timeframe} data from {csv_path.name}...")

    try:
        df = pd.read_csv(csv_path)

        records = []
        for idx, row in df.iterrows():
            try:
                # Parse date
                date_str = str(row['Date']) if 'Date' in row else str(row['Datetime'])
                timestamp = parse_csv_date(date_str)

                # Create record
                record = {
                    'symbol': symbol,
                    'timestamp': timestamp,
                    'timeframe': timeframe,
                    'open_price': Decimal(str(row['Open'])),
                    'high_price': Decimal(str(row['High'])),
                    'low_price': Decimal(str(row['Low'])),
                    'close_price': Decimal(str(row['Close'])),
                    'volume': int(row['Volume']),
                    'data_source': YAHOO_FINANCE,
                    'is_validated': True,
                }

                # Calculate change_percent
                if record['open_price'] > 0:
                    change = (record['close_price'] - record['open_price']) / record['open_price'] * 100
                    record['change_percent'] = Decimal(str(change))

                records.append(record)

            except Exception as e:
                logger.warning(f"Failed to parse row {idx} in {csv_path}: {e}")
                continue

        print(f"    ✓ Loaded {len(records)} records")
        return records

    except Exception as e:
        print(f"    ✗ Error loading {csv_path}: {e}")
        return []


def load_all_bank_data():
    """Load all bank data from CSV files"""

    historical_path = Path(__file__).parent / "historical"
    if not historical_path.exists():
        print(f"✗ Historical data directory not found: {historical_path}")
        return

    all_records = []
    stats = {
        'banks_processed': 0,
        'daily_records': 0,
        'intraday_records': 0,
        'total_records': 0,
        'errors': 0
    }

    # Process each bank directory
    for bank_dir in sorted(historical_path.iterdir()):
        if not bank_dir.is_dir():
            continue

        symbol = bank_dir.name
        print(f"\n[{stats['banks_processed'] + 1}] Processing {symbol}")
        print("-" * 70)

        bank_records = []

        # Load daily data
        daily_csv = bank_dir / "daily" / f"{symbol}_daily.csv"
        if daily_csv.exists():
            daily_data = load_csv_file(daily_csv, symbol, "1day")
            bank_records.extend(daily_data)
            stats['daily_records'] += len(daily_data)

        # Load 15-min data
        intraday_csv = bank_dir / "15min" / f"{symbol}_15min.csv"
        if intraday_csv.exists():
            intraday_data = load_csv_file(intraday_csv, symbol, "15min")
            bank_records.extend(intraday_data)
            stats['intraday_records'] += len(intraday_data)

        all_records.extend(bank_records)
        stats['banks_processed'] += 1

        print(f"    Total for {symbol}: {len(bank_records)} records")

    # Insert into database
    print(f"\n{'='*70}")
    print("INSERTING INTO DATABASE")
    print(f"{'='*70}")

    # Initialize database tables directly
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base

    DATABASE_URL = "sqlite:///./data/niraj.db"
    engine = create_engine(DATABASE_URL, echo=False)
    Base = declarative_base()

    # Define the table structure directly
    from sqlalchemy import Column, String, DateTime, Integer, Numeric, Index
    import uuid

    class MarketDataORM(Base):
        __tablename__ = "market_data"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        symbol = Column(String(20), nullable=False, index=True)
        timestamp = Column(DateTime, nullable=False, index=True)
        timeframe = Column(String(20), nullable=False, index=True)

        # OHLCV Data
        open_price = Column(Numeric(15, 2), nullable=False)
        high_price = Column(Numeric(15, 2), nullable=False)
        low_price = Column(Numeric(15, 2), nullable=False)
        close_price = Column(Numeric(15, 2), nullable=False)
        volume = Column(Integer, nullable=False, default=0)

        # Additional Fields
        change_percent = Column(Numeric(8, 4), nullable=True)
        vwap = Column(Numeric(15, 2), nullable=True)
        total_traded_value = Column(Numeric(20, 2), nullable=True)

        # Data Quality
        data_source = Column(String(20), nullable=False)
        is_validated = Column(Integer, nullable=False, default=0)
        created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

        # Composite indexes for performance
        __table_args__ = (
            Index("idx_symbol_timestamp_timeframe", "symbol", "timestamp", "timeframe"),
            Index("idx_timestamp_symbol", "timestamp", "symbol"),
            Index("idx_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp"),
        )

    # Create tables
    Base.metadata.create_all(engine)

    # Get session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        batch_size = 1000
        total_inserted = 0

        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i + batch_size]

            for record in batch:
                try:
                    # Create ORM object
                    market_data = MarketDataORM(
                        symbol=record['symbol'],
                        timestamp=record['timestamp'],
                        timeframe=record['timeframe'],
                        open_price=record['open_price'],
                        high_price=record['high_price'],
                        low_price=record['low_price'],
                        close_price=record['close_price'],
                        volume=record['volume'],
                        change_percent=record.get('change_percent'),
                        data_source=record['data_source'],
                        is_validated=record['is_validated']
                    )

                    session.add(market_data)
                    total_inserted += 1

                except Exception as e:
                    logger.error(f"Failed to create record for {record['symbol']}: {e}")
                    stats['errors'] += 1
                    continue

            # Commit batch
            session.commit()
            print(f"    ✓ Inserted batch {i//batch_size + 1}: {len(batch)} records")

        stats['total_records'] = total_inserted

    except Exception as e:
        session.rollback()
        print(f"✗ Database error: {e}")
        raise
    finally:
        session.close()

    # Print summary
    print(f"\n{'='*70}")
    print("LOAD SUMMARY")
    print(f"{'='*70}")
    print(f"Banks Processed:    {stats['banks_processed']}")
    print(f"Daily Records:      {stats['daily_records']:,}")
    print(f"Intraday Records:   {stats['intraday_records']:,}")
    print(f"Total Records:      {stats['total_records']:,}")
    print(f"Errors:             {stats['errors']}")
    print(f"{'='*70}")

    return stats


def main():
    """Main entry point"""
    try:
        stats = load_all_bank_data()

        if stats and stats['total_records'] > 0:
            print("✅ Data loading completed successfully!")
            print(f"\n📊 Database now contains {stats['total_records']:,} market data records")
        else:
            print("⚠ No data was loaded")

    except KeyboardInterrupt:
        print("\n\n⚠ Data loading interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
