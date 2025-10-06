# System Monitoring & Hardware Control Features

## Overview
NIRAJ now includes comprehensive system monitoring and hardware control features integrated into the real-time trading dashboard. All metrics update every second alongside trading data.

## Features

### 1. Real-Time System Statistics
The dashboard displays live system health metrics:

#### CPU Monitoring
- **CPU Usage**: Real-time CPU utilization percentage with color-coded indicators
- **Core Count**: Number of logical CPU cores
- **Load Average**: 1-minute load average
- **Visual Bar**: Progress bar showing CPU load at a glance
- **Color Coding**:
  - 🟢 Green: < 50% (Optimal)
  - 🟡 Yellow: 50-75% (Moderate)
  - 🔴 Red: > 75% (High Load)

#### Memory Monitoring
- **RAM Usage**: Memory utilization with used/total gigabytes
- **Percentage**: Memory usage percentage with visual bar
- **Swap Usage**: Swap memory statistics
- **Color Coding**: Same thresholds as CPU

#### Disk & Network
- **Disk Usage**: Storage utilization with used/total capacity
- **Network**: Upload and download traffic since dashboard start (in MB)
- **Real-time Updates**: Network counters update every second

#### GPU Monitoring (NVIDIA)
Requires NVIDIA GPU with nvidia-smi utility:
- **GPU Name**: Graphics card model
- **GPU Load**: Utilization percentage
- **GPU Memory**: VRAM usage percentage
- **Temperature**: GPU temperature in Celsius
- **Fan Speed**: Current fan RPM percentage (if available)
- **Color Coding**:
  - Temperature thresholds: 60°C / 75°C / 85°C
  - Load/Memory: Standard 50% / 75% / 90%

#### Temperature Sensors
- Displays up to 3 temperature sensors (if available via psutil)
- Common sensors: CPU package temp, cores, etc.
- Graceful fallback if sensors unavailable

#### System Health Indicator
- **Overall Status**: Aggregated health based on average of CPU/Memory/Disk
- **Status Levels**:
  - 🟢 OPTIMAL: Average < 50%
  - 🟡 MODERATE: Average 50-75%
  - 🔴 HIGH LOAD: Average > 75%

### 2. Fan Speed Control
Control NVIDIA GPU fan speed directly from the command line.

#### Usage
```bash
# Set fan to maximum
python niraj.py --terminal-mode --fan-speed max

# Set specific percentage
python niraj.py --terminal-mode --fan-speed 70
python niraj.py --terminal-mode --fan-speed 50
python niraj.py --terminal-mode --fan-speed 30
```

#### Options
- `max` or `100`: 100% fan speed
- `70`: 70% fan speed
- `50`: 50% fan speed (balanced)
- `30`: 30% fan speed (quiet)
- `10`: 10% fan speed (minimal cooling)

#### Requirements
- NVIDIA GPU with proprietary drivers
- `nvidia-settings` utility installed
- Appropriate permissions (may require sudo on some systems)
- **Note**: Many laptop GPUs have locked fan control; feature is best-effort

#### Warnings
The system will display appropriate messages:
- ✅ Success: Fan speed set successfully
- ⚠️ Warning: GPU fan control unavailable (needs nvidia-settings + permissions)

### 3. Paper Trading & Real Trading Modes

#### Start Paper Trading Dashboard
```bash
# With system stats and monitoring
python niraj.py --terminal-mode --paper-trading

# With custom fan speed
python niraj.py --terminal-mode --paper-trading --fan-speed 50
```

#### Start Real Trading Dashboard
```bash
# CAUTION: Uses real money!
python niraj.py --terminal-mode --real-trading

# With monitoring
python niraj.py --terminal-mode --real-trading --fan-speed 70
```

#### Dashboard Features
- ✅ Updates every 1 second
- ✅ Account balances (Dhan + Angel One)
- ✅ Live PNL tracking
- ✅ Trade counts (winning/losing)
- ✅ Market data (Bank Nifty with trend)
- ✅ Latest news headlines (5 most recent)
- ✅ AI engine status (training/thinking/confidence)
- ✅ Chart pattern indicators
- ✅ System health metrics (NEW)
- ✅ GPU monitoring (NEW)

### 4. Terminal vs Web Mode Toggle

#### Benefits of Terminal Mode
- **Reduced CPU Load**: No browser rendering
- **Lower GPU Usage**: No graphics acceleration needed
- **Faster Updates**: Direct terminal output
- **Lower Memory**: Minimal overhead
- **Better for Remote**: Works over SSH

#### Switching Modes
```python
# In future implementation, runtime toggle will be available
dashboard.toggle_mode()  # Switches between terminal and web
```

Current mode is set at startup:
```bash
# Terminal mode (default with --terminal-mode)
python niraj.py --terminal-mode

# Dashboard only (requires running backend)
python niraj.py --dashboard-only
```

## Installation Requirements

### Core Dependencies
```bash
# System monitoring
pip install psutil

# Already installed (trading system)
pip install requests colorama
```

### Optional Dependencies
```bash
# For GPU monitoring (NVIDIA only)
sudo apt install nvidia-utils  # Debian/Ubuntu
# or
sudo dnf install nvidia-utils  # Fedora/RHEL

# For fan control (NVIDIA only)
sudo apt install nvidia-settings  # Debian/Ubuntu
```

## Usage Examples

### Example 1: Full Monitoring Dashboard
```bash
# Paper trading with system monitoring and fan control
python niraj.py --terminal-mode --paper-trading --fan-speed 70
```

### Example 2: Real Trading with Minimal Fan Noise
```bash
# Real trading with quiet fan settings
python niraj.py --terminal-mode --real-trading --fan-speed 30
```

### Example 3: Dashboard-Only Mode
```bash
# Start backend separately
python niraj.py --enable-api --enable-redis

# Then in another terminal, start dashboard only
python niraj.py --dashboard-only --paper-trading
```

### Example 4: Development Mode with All Services
```bash
# Full stack with maximum cooling
python niraj.py --enable-api --enable-frontend --enable-redis --enable-ollama --fan-speed max
```

## Display Layout

```
═══════════════════════════════════════════════════════════════
        NIRAJ TRADING SYSTEM - LIVE DASHBOARD
═══════════════════════════════════════════════════════════════

🔴 PAPER TRADING (₹10,000) | Terminal Mode
🕐 2025-10-05 14:30:45 IST

┌─ ACCOUNT BALANCES ────────────────────────────────────────┐
│ 💰 DHAN:       ₹10,000.00  |  PNL: ₹+125.50                │
│ 💰 ANGEL ONE:  ₹10,000.00  |  PNL: ₹+87.30                 │
│ TOTAL:         ₹20,000.00  |  PNL: ₹+212.80                │
└────────────────────────────────────────────────────────────┘

┌─ MARKET DATA ─────────────────────────────────────────────┐
│ 📈 BANK NIFTY: 45,234.50  +234.50 (+0.52%)                │
│ 📊 TREND:      BULLISH ▲                                   │
│ 📉 VOLATILITY: LOW                                         │
└────────────────────────────────────────────────────────────┘

┌─ SYSTEM HEALTH & PERFORMANCE ─────────────────────────────┐
│ 🔥 CPU: 35.2% ███████████░░░░░ (8c) Load: 2.45            │
│ 💾 RAM: 62.8% ████████████░░░░ 10.1/16.0G                 │
│ 💿 DSK: 45.3%  225.3/512.0G | NET ↑12.5M ↓45.3M           │
│ 🎮 GPU: NVIDIA GeForce RTX 3060                            │
│    └─ Load: 25.0% Mem: 30.0% Temp: 65°C Fan: 45%          │
│ 🟢 System Health: OPTIMAL (Avg: 47.8%)                     │
└────────────────────────────────────────────────────────────┘
```

## Performance Impact

### Resource Usage
- **CPU**: < 2% additional (system stats collection)
- **Memory**: ~5MB additional (psutil + data structures)
- **Disk I/O**: Negligible (only reads /proc files)
- **Network**: None (local monitoring only)

### Update Frequency
- All metrics update every 1 second
- GPU queries use 1.5s timeout (non-blocking)
- Network stats calculate delta since dashboard start

## Troubleshooting

### GPU Not Detected
**Symptom**: "GPU: N/A (No NVIDIA GPU detected)"

**Solutions**:
1. Install nvidia-smi: `sudo apt install nvidia-utils`
2. Check GPU: `nvidia-smi` in terminal
3. Update drivers: Use proprietary NVIDIA drivers
4. Verify CUDA toolkit installation

### Fan Control Not Working
**Symptom**: "GPU fan control unavailable"

**Solutions**:
1. Install nvidia-settings: `sudo apt install nvidia-settings`
2. Check permissions: May need sudo on some systems
3. Enable manual control: `nvidia-settings -a '[gpu:0]/GPUFanControlState=1'`
4. **Laptop Note**: Many laptop BIOSes lock fan control for safety

### High CPU Usage
**Symptom**: Dashboard causing high CPU usage

**Solutions**:
1. Use terminal mode instead of web mode
2. Increase update interval (future feature)
3. Disable system stats (future feature)
4. Close other applications

### psutil Not Found
**Symptom**: System stats not displaying

**Solutions**:
```bash
# Install psutil
pip install psutil

# Or in backend directory
cd backend
poetry add psutil
```

## Safety Notes

### Fan Control Safety
- ⚠️ Manual fan control can void warranty
- ⚠️ Never set fan below 10% under load
- ⚠️ Monitor temperatures when using custom fan speeds
- ⚠️ System will auto-protect if temps get critical
- ✅ Safe defaults: 50-70% for balanced operation

### Real Trading Safety
- 🚨 Real trading uses actual money
- 🚨 Always test with paper trading first
- 🚨 Set appropriate stop losses
- 🚨 Never trade without understanding risks
- ✅ Paper trading is 100% safe for learning

## Future Enhancements

### Planned Features
- [ ] Runtime toggle between terminal/web mode
- [ ] Configurable update intervals
- [ ] Historical performance graphs
- [ ] Alert thresholds for system metrics
- [ ] Multi-GPU support
- [ ] AMD GPU support (via rocm-smi)
- [ ] Export metrics to CSV/JSON
- [ ] System stats API endpoints
- [ ] Mobile dashboard view
- [ ] Voice alerts for critical thresholds

## API Integration

System stats will be available via REST API (future):

```python
# Get current system stats
GET /api/v1/system/stats

# Response
{
  "cpu_percent": 35.2,
  "memory_percent": 62.8,
  "disk_percent": 45.3,
  "gpu": {
    "name": "NVIDIA GeForce RTX 3060",
    "utilization": 25.0,
    "temperature": 65
  }
}
```

## Contributing

To extend system monitoring features:

1. Add new metrics to `SystemStats` dataclass
2. Implement collection in `_fetch_system_stats()`
3. Add rendering in `_print_system_stats()`
4. Update this documentation

## License

Same as main NIRAJ project.

## Support

For issues related to system monitoring:
- Check logs: `logs/niraj.log`
- Verify psutil installation
- Check nvidia-smi availability
- Review this documentation

---

**Last Updated**: October 5, 2025
**Version**: 1.0.0
**Status**: ✅ Fully Operational
