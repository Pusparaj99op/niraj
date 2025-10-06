# NIRAJ Trading Dashboard - User Guide

## 🚀 New Features Added

The NIRAJ trading system now includes a **real-time trading dashboard** with powerful features:

### ✨ Key Features

1. **Real-Time Data Updates (1-second refresh)**
   - All trading data updates every 1 second automatically
   - Live market data from Dhan and Angel One brokers
   - Real-time PNL calculations
   - Live news feed integration
   - AI engine status monitoring

2. **Paper Trading Mode**
   - Start with ₹10,000 virtual balance
   - Practice trading without risk
   - Full simulation of real trading experience
   - Track performance and strategy effectiveness

3. **Real Trading Mode**
   - Connect to actual Dhan and Angel One accounts
   - Execute real trades with real money
   - Real-time balance and position tracking
   - Full risk management features

4. **Terminal Mode / Web Mode Toggle**
   - **Terminal Mode**: Reduces CPU/GPU load by displaying dashboard in terminal only
   - **Web Mode**: Enables frontend for graphical interface
   - Switch between modes dynamically
   - Optimize resource usage based on your needs

5. **Comprehensive Dashboard Display**
   - **Account Balances**: Dhan and Angel One balances with PNL
   - **Market Data**: Bank Nifty price, trend, volatility
   - **Trades**: Active positions and trade count
   - **PNL Summary**: Today's profit/loss and win rate
   - **News Headlines**: Latest 5 market news items
   - **AI Status**: AI engine activity, training status, confidence level
   - **Chart Patterns**: Bank Nifty trend indicators

---

## 📋 Usage Examples

### 1. Start Paper Trading Dashboard (Terminal Mode)

```bash
python niraj.py --terminal-mode --paper-trading
```

This will:
- Start backend API server
- Start Redis cache
- Launch real-time trading dashboard in terminal
- Use ₹10,000 virtual balance
- Update every 1 second

### 2. Start Real Trading Dashboard (Use with Caution!)

```bash
python niraj.py --terminal-mode --real-trading
```

⚠️ **WARNING**: This mode uses actual funds! Make sure your broker credentials are correctly configured.

### 3. Dashboard Only (Backend Already Running)

```bash
python niraj.py --dashboard-only --paper-trading
```

Use this if backend is already running separately.

### 4. Interactive Menu Mode

```bash
python niraj.py --menu
```

Then select:
- **Option 10**: Paper Trading Dashboard
- **Option 11**: Real Trading Dashboard

---

## 🎮 Dashboard Controls

Once the dashboard is running:

- **Automatic Refresh**: Every 1 second (no manual action needed)
- **Stop**: Press `Ctrl+C` to gracefully stop the dashboard
- **Switch Modes**: (Future) Press 'W' to toggle between Terminal/Web mode

---

## 📊 Dashboard Information Display

### Account Section
```
┌─ ACCOUNT BALANCES ────────────────────────────────────────┐
│ 💰 DHAN:       ₹10,000.00  |  PNL: ₹0.00
│ 💰 ANGEL ONE:  ₹10,000.00  |  PNL: ₹0.00
│ TOTAL:      ₹20,000.00  |  PNL: ₹0.00
└────────────────────────────────────────────────────────────┘
```

### Market Data Section
```
┌─ MARKET DATA ─────────────────────────────────────────────┐
│ 📈 BANK NIFTY: 45,234.50  +123.45 (+0.27%)
│ 📊 TREND:      BULLISH ▲
│ 📉 VOLATILITY: MODERATE
└────────────────────────────────────────────────────────────┘
```

### Positions & Trades Section
```
┌─ POSITIONS & TRADES ──────────────────────────────────────┐
│ DHAN:       2 positions | 5 trades today
│ ANGEL ONE:  1 positions | 3 trades today
│ TOTAL:      8 trades | W: 5 | L: 3
└────────────────────────────────────────────────────────────┘
```

### PNL Summary Section
```
┌─ PNL SUMMARY ─────────────────────────────────────────────┐
│ TODAY'S PNL:  ₹+1,234.56
│ WIN RATE:     62.5%
└────────────────────────────────────────────────────────────┘
```

### News Section
```
┌─ NEWS HEADLINES ──────────────────────────────────────────┐
│ 1. Markets rally on positive GDP data...
│ 2. Banking stocks surge amid rate cut expectations...
│ 3. IT sector sees strong quarterly earnings...
│ 4. FII inflows continue for third consecutive week...
│ 5. RBI maintains policy rates in latest meeting...
└────────────────────────────────────────────────────────────┘
```

### AI Engine Status Section
```
┌─ AI ENGINE STATUS ────────────────────────────────────────┐
│ STATUS:     🟢 ACTIVE
│ TASK:       Analyzing market patterns
│ CONFIDENCE: 87.5%
└────────────────────────────────────────────────────────────┘
```

### Chart Pattern Section
```
┌─ BANK NIFTY CHART PATTERN ────────────────────────────────┐
│     📈📈📈 UPTREND - Support at previous low
└────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

### Setting Up Broker Credentials

Edit `/home/pranay/Music/niraj/backend/.env`:

```env
# Dhan Credentials
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Angel One Credentials
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
```

### API Endpoints Used

The dashboard fetches data from these backend endpoints:

- **Balances**: `/api/v1/portfolio/balance/{broker}`
- **Market Data**: `/api/v1/market-data/{symbol}/ltp`
- **News**: `/api/v1/news/headlines`
- **AI Status**: `/api/v1/ai/status`
- **Trades**: `/api/v1/trades`
- **Positions**: `/api/v1/portfolio/positions`

---

## 🔧 Terminal Mode vs Web Mode

### Terminal Mode (Default)
- **CPU/GPU Usage**: LOW ✅
- **Interface**: Text-based terminal dashboard
- **Updates**: Real-time in terminal
- **Best For**:
  - Running on servers
  - Low-resource environments
  - When you want minimal overhead
  - SSH sessions

### Web Mode
- **CPU/GPU Usage**: HIGHER (Frontend running)
- **Interface**: Rich graphical web interface
- **Updates**: Real-time via WebSockets
- **Best For**:
  - Desktop/laptop usage
  - When visual charts are needed
  - Multiple monitor setups
  - Detailed analysis

### Switching Between Modes

```python
# In future updates, press 'W' key in dashboard to toggle
# Currently, restart with different mode
```

---

## 📈 Performance Metrics

The 1-second update interval provides:

- Real-time trade execution monitoring
- Immediate PNL updates
- Live market trend analysis
- Instant news feed updates
- AI decision-making transparency

---

## 🛡️ Safety Features

### Paper Trading Mode
- No real money at risk
- Perfect for testing strategies
- Learn system behavior
- Virtual ₹10,000 balance

### Real Trading Mode
- Confirmation prompt required
- Full audit logging
- Risk management checks
- Position size limits

---

## 🐛 Troubleshooting

### Dashboard Not Updating
1. Check if backend is running: `python niraj.py status`
2. Verify Redis is running
3. Check network connectivity
4. Review logs: `/home/pranay/Music/niraj/logs/backend.log`

### No Market Data
1. Verify broker API credentials
2. Check if market is open
3. Ensure API rate limits not exceeded
4. Test endpoint: `curl http://localhost:8000/api/v1/market-data/status`

### News Not Loading
1. Check news API configuration
2. Verify internet connectivity
3. Test endpoint: `curl http://localhost:8000/api/v1/news/health`

### AI Status Not Showing
1. Ensure Ollama is running
2. Check AI integration in backend
3. Verify model is loaded
4. Test endpoint: `curl http://localhost:8000/api/v1/ai/status`

---

## 📝 Examples

### Example 1: Start Paper Trading and Monitor

```bash
# Terminal 1: Start paper trading dashboard
python niraj.py --terminal-mode --paper-trading

# Dashboard will show:
# - ₹10,000 starting balance on each broker
# - Real-time market data
# - News updates every second
# - AI thinking process
```

### Example 2: Use Interactive Menu

```bash
python niraj.py --menu

# Select option 10 for Paper Trading
# Dashboard launches automatically
# Press Ctrl+C to return to menu
```

### Example 3: Switch to Web Mode (Future)

```bash
# Start in terminal mode
python niraj.py --terminal-mode --paper-trading

# Press 'W' to switch to web mode
# Frontend will start automatically
# Dashboard continues updating in web interface
```

---

## 🎯 Best Practices

1. **Always Start with Paper Trading**
   - Test your strategies risk-free
   - Learn the system
   - Understand the dashboard

2. **Monitor System Resources**
   - Use terminal mode for lower overhead
   - Switch to web mode when needed
   - Close unused services

3. **Review Logs Regularly**
   - Check for errors or warnings
   - Monitor API rate limits
   - Track trading performance

4. **Keep Credentials Secure**
   - Use environment variables
   - Never commit credentials to git
   - Rotate keys regularly

5. **Test API Connectivity**
   - Use built-in API testing: Option 7 in menu
   - Verify broker connections before trading
   - Check health endpoints

---

## 🚦 Command Reference

### Command-Line Options

```bash
# Paper trading in terminal
python niraj.py --terminal-mode --paper-trading

# Real trading in terminal (CAUTION!)
python niraj.py --terminal-mode --real-trading

# Dashboard only (backend must be running)
python niraj.py --dashboard-only --paper-trading

# Interactive menu
python niraj.py --menu

# Traditional service start
python niraj.py --enable-api --enable-frontend

# Show status
python niraj.py status

# Stop all services
python niraj.py stop
```

---

## 📚 Additional Resources

- **Full Documentation**: `/home/pranay/Music/niraj/docs/`
- **API Reference**: `/home/pranay/Music/niraj/docs/API_REFERENCE.md`
- **Architecture**: `/home/pranay/Music/niraj/docs/ARCHITECTURE.md`
- **Developer Guide**: `/home/pranay/Music/niraj/docs/DEVELOPER_GUIDE.md`

---

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs in `/home/pranay/Music/niraj/logs/`
3. Test APIs using menu option 7
4. Check backend health: `http://localhost:8000/health`

---

## ⚡ Quick Start

```bash
# 1. Install dependencies (first time only)
python niraj.py install

# 2. Start paper trading dashboard
python niraj.py --terminal-mode --paper-trading

# 3. Watch real-time updates!
# Press Ctrl+C to stop
```

---

**Happy Trading! 🚀📈💰**
