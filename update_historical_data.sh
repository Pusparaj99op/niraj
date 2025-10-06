#!/bin/bash
#
# Update Bank Nifty Historical Data
# This script re-downloads the latest Bank Nifty data
#

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   Bank Nifty Historical Data Update Script        ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH"
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo ""

# Check if yfinance is installed
python -c "import yfinance" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  yfinance not installed. Installing..."
    pip install yfinance
    echo ""
fi

# Run the download script
echo "📥 Downloading latest Bank Nifty data..."
echo ""
python download_banknifty_yfinance.py

# Check if download was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════╗"
    echo "║   ✓ Update Complete!                              ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo ""
    echo "Files saved in: ./historical/"
    echo ""
    ls -lh historical/ | grep BANKNIFTY | tail -3
    echo ""
else
    echo ""
    echo "╔════════════════════════════════════════════════════╗"
    echo "║   ❌ Update Failed!                               ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo ""
    echo "Please check the error messages above."
    exit 1
fi
