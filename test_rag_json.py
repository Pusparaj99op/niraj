"""Quick test of RAG JSON data"""
import json

print("\n🔍 Testing RAG JSON Data\n" + "="*60)

# Test 1: Load combined dataset
print("\n1. Loading combined dataset...")
with open('historical/rag_json/all_banks_rag_combined.json', 'r') as f:
    dataset = json.load(f)

metadata = dataset['metadata']
statistics = dataset['statistics']

print(f"   ✓ Dataset: {metadata['dataset']}")
print(f"   ✓ Total banks: {metadata['total_banks']}")
print(f"   ✓ Total records: {statistics['total_records']:,}")
print(f"   ✓ Daily records: {statistics['daily_records']:,}")
print(f"   ✓ Intraday records: {statistics['intraday_records']:,}")

# Test 2: Load individual bank
print("\n2. Loading HDFC Bank daily data...")
with open('historical/rag_json/HDFCBANK_daily_rag.json', 'r') as f:
    hdfc_data = json.load(f)

print(f"   ✓ Records: {len(hdfc_data):,}")
print(f"   ✓ Date range: {hdfc_data[0]['timestamp']} to {hdfc_data[-1]['timestamp']}")

# Test 3: Sample entry
print("\n3. Sample entry structure:")
sample = hdfc_data[-1]
print(f"   ✓ ID: {sample['id']}")
print(f"   ✓ Bank: {sample['bank_name']}")
print(f"   ✓ Date: {sample['timestamp']}")
print(f"   ✓ Close: ₹{sample['ohlcv']['close']:.2f}")
print(f"   ✓ Trend: {sample['metrics']['trend']}")
print(f"   ✓ Text: {sample['text'][:100]}...")

# Test 4: Filter by trend
print("\n4. Filtering by trend...")
bullish = [e for e in hdfc_data if e['metrics']['trend'] == 'bullish']
bearish = [e for e in hdfc_data if e['metrics']['trend'] == 'bearish']
neutral = [e for e in hdfc_data if e['metrics']['trend'] == 'neutral']

print(f"   ✓ Bullish days: {len(bullish):,}")
print(f"   ✓ Bearish days: {len(bearish):,}")
print(f"   ✓ Neutral days: {len(neutral):,}")

# Test 5: High volatility days
print("\n5. High volatility analysis...")
high_vol = [e for e in hdfc_data if e['metrics']['volatility_percent'] > 5.0]
print(f"   ✓ High volatility days (>5%): {len(high_vol):,}")

if high_vol:
    avg_vol = sum(e['metrics']['volatility_percent'] for e in high_vol) / len(high_vol)
    print(f"   ✓ Average volatility: {avg_vol:.2f}%")

# Test 6: Recent data (2025)
print("\n6. Recent data (2025)...")
data_2025 = [e for e in hdfc_data if e['timestamp'].startswith('2025')]
print(f"   ✓ 2025 records: {len(data_2025):,}")

if data_2025:
    bullish_2025 = sum(1 for e in data_2025 if e['metrics']['trend'] == 'bullish')
    print(f"   ✓ Bullish in 2025: {bullish_2025} ({bullish_2025/len(data_2025)*100:.1f}%)")

print("\n" + "="*60)
print("✅ All tests passed! RAG JSON data is ready to use.\n")
