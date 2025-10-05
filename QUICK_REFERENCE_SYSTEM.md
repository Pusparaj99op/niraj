# NIRAJ Quick Reference Card

## 🚀 Quick Start Commands

### Launch Trading Dashboard
```bash
# Paper Trading (Safe, ₹10,000 virtual)
python niraj.py --terminal-mode --paper-trading

# Real Trading (⚠️ Uses real money!)
python niraj.py --terminal-mode --real-trading
```

### GPU Fan Control
```bash
# Maximum cooling
python niraj.py --terminal-mode --fan-speed max

# Balanced (70%)
python niraj.py --terminal-mode --paper-trading --fan-speed 70

# Quiet mode (30%)
python niraj.py --terminal-mode --paper-trading --fan-speed 30
```

### Service Management
```bash
# Check status
python niraj.py status

# Start services
python niraj.py --enable-api --enable-redis

# Stop all
python niraj.py stop

# Install dependencies
python niraj.py install
```

## 📊 Dashboard Sections

### Account Info (Updates: 1s)
- 💰 Dhan Balance & PNL
- 💰 Angel One Balance & PNL
- 📈 Total Equity & PNL

### Market Data (Updates: 1s)
- 📈 Bank Nifty Price
- 📊 Trend (Bullish/Bearish/Neutral)
- 📉 Volatility Level
- 🎯 Chart Patterns

### System Health (Updates: 1s)
- 🔥 CPU Usage & Load
- 💾 RAM & Swap Usage
- 💿 Disk & Network
- 🎮 GPU Stats (NVIDIA)
- 🌡️ Temperature Sensors
- 🟢 Overall Health Status

### AI Engine (Updates: 1s)
- 🤖 Active/Inactive Status
- 🧠 Training State
- 💭 Current Task
- 📊 Confidence Level
- 📡 Trading Signals

### News Feed (Updates: 1s)
- 📰 Latest 5 Headlines
- 🕐 Real-time Updates

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Stop dashboard / Exit |
| `Enter` | Continue after info |
| `0-9` | Menu selection |
| `help` | Show help (in menus) |

## 🎨 Color Indicators

### CPU/Memory/Disk
- 🟢 **Green**: < 50% (Optimal)
- 🟡 **Yellow**: 50-75% (Moderate)
- 🔴 **Red**: > 75% (High Load)

### GPU Temperature
- 🟢 **Green**: < 60°C (Cool)
- 🟡 **Yellow**: 60-75°C (Warm)
- 🔴 **Red**: > 75°C (Hot)

### PNL
- 🟢 **Green**: Positive gain
- 🔴 **Red**: Loss

### AI Confidence
- 🟢 **Green**: > 70%
- 🟡 **Yellow**: 40-70%
- 🔴 **Red**: < 40%

## 🛠️ System Requirements

### Minimum
- Python 3.8+
- 4GB RAM
- 10GB Disk Space

### Recommended
- Python 3.10+
- 8GB+ RAM
- 20GB+ Disk Space
- NVIDIA GPU (for GPU features)

### Dependencies
```bash
pip install psutil colorama requests
```

### Optional (GPU)
```bash
# Ubuntu/Debian
sudo apt install nvidia-utils nvidia-settings

# Fedora/RHEL
sudo dnf install nvidia-utils
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `niraj.py` | Main launcher |
| `niraj-runner.json` | Service configuration |
| `logs/niraj.log` | System logs |
| `backend/config/*.yaml` | Backend config |
| `SYSTEM_MONITORING_FEATURES.md` | Full documentation |

## 🔧 Configuration

### Change Environment
```bash
--mode development    # Dev mode (default)
--mode production     # Production
--mode testing        # Testing
```

### Custom Config
```bash
--config custom.json  # Use custom config file
```

## 🐛 Troubleshooting

### GPU Not Detected
```bash
# Check GPU
nvidia-smi

# Install driver
sudo ubuntu-drivers autoinstall
```

### Fan Control Not Working
```bash
# Install nvidia-settings
sudo apt install nvidia-settings

# Test manually
nvidia-settings -a '[gpu:0]/GPUFanControlState=1'
nvidia-settings -a '[fan:0]/GPUTargetFanSpeed=70'
```

### Port Already in Use
```bash
# Find process
sudo lsof -i :8000

# Kill process
kill -9 <PID>
```

### Permission Denied
```bash
# Run with sudo (if needed)
sudo python niraj.py --terminal-mode
```

## 📊 Performance Tips

### Reduce CPU Load
1. Use `--terminal-mode` (vs web interface)
2. Stop frontend if not needed
3. Lower fan speed for less noise
4. Close unnecessary services

### Optimize Memory
1. Stop Ollama if AI not needed
2. Clear Redis cache periodically
3. Restart services weekly

### Best Settings for 24/7
```bash
# Recommended
python niraj.py --terminal-mode --paper-trading --fan-speed 50
```

## 🔒 Safety Checklist

### Before Real Trading
- [ ] Tested with paper trading
- [ ] Backend services running
- [ ] API credentials configured
- [ ] Stop-loss limits set
- [ ] Risk management plan ready
- [ ] Monitor system resources
- [ ] Backup configuration

### System Health
- [ ] CPU < 80%
- [ ] RAM < 80%
- [ ] GPU Temp < 80°C
- [ ] Disk Space > 20%
- [ ] Network stable

## 📞 Get Help

```bash
# Show help
python niraj.py --help

# Check documentation
cat SYSTEM_MONITORING_FEATURES.md

# View logs
tail -f logs/niraj.log
```

## 🎯 Common Use Cases

### Development
```bash
python niraj.py --enable-api --enable-frontend --enable-redis
```

### Testing Strategies
```bash
python niraj.py --terminal-mode --paper-trading --fan-speed 50
```

### Production Trading
```bash
python niraj.py --mode production --terminal-mode --real-trading --fan-speed 70
```

### Monitoring Only
```bash
python niraj.py --dashboard-only
```

## 📈 Performance Metrics

| Metric | Typical | Max |
|--------|---------|-----|
| CPU Usage | 2-5% | 15% |
| RAM Usage | 200MB | 500MB |
| Update Rate | 1 sec | 1 sec |
| GPU Query | 1.5s timeout | 1.5s |

## 🔄 Update Frequency

All metrics update every **1 second**:
- ✅ Account balances
- ✅ Market data
- ✅ System stats
- ✅ News feed
- ✅ AI status
- ✅ PNL calculations

---

**Version**: 1.0.0
**Last Updated**: October 5, 2025
**Status**: ✅ Production Ready
