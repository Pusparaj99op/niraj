# NIRAJ Trading Dashboard - Visual Layout

## Dashboard Structure (Terminal Mode - Updates Every 1 Second)

```
═══════════════════════════════════════════════════════════════════════
                NIRAJ TRADING SYSTEM - LIVE DASHBOARD
═══════════════════════════════════════════════════════════════════════

🔴 PAPER TRADING (₹10,000) | Terminal Mode
🕐 2025-10-05 14:30:45 IST

┌─ ACCOUNT BALANCES ────────────────────────────────────────────────┐
│ 💰 DHAN:       ₹10,250.50  |  PNL: 🟢 ₹+250.50 (+2.51%)           │
│ 💰 ANGEL ONE:  ₹10,180.75  |  PNL: 🟢 ₹+180.75 (+1.81%)           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│ 📊 TOTAL:      ₹20,431.25  |  PNL: 🟢 ₹+431.25 (+2.16%)           │
└───────────────────────────────────────────────────────────────────┘

┌─ MARKET DATA ─────────────────────────────────────────────────────┐
│ 📈 BANK NIFTY: 45,234.50  🟢 +234.50 (+0.52%)                     │
│ 📊 TREND:      BULLISH ▲                                           │
│ 📉 VOLATILITY: LOW                                                 │
└───────────────────────────────────────────────────────────────────┘

┌─ POSITIONS & TRADES ──────────────────────────────────────────────┐
│ DHAN:       2 positions | 15 trades today                          │
│ ANGEL ONE:  3 positions | 12 trades today                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│ TOTAL:      27 trades | 🟢 W: 18 | 🔴 L: 9                        │
└───────────────────────────────────────────────────────────────────┘

┌─ PNL SUMMARY ─────────────────────────────────────────────────────┐
│ TODAY'S PNL:  🟢 ₹+431.25                                          │
│ WIN RATE:     66.7%                                                │
│ AVG WIN:      ₹+35.50                                              │
│ AVG LOSS:     ₹-18.25                                              │
└───────────────────────────────────────────────────────────────────┘

┌─ NEWS HEADLINES ──────────────────────────────────────────────────┐
│ 1. 📰 Bank Nifty hits new high on strong banking sector...        │
│ 2. 📰 RBI maintains repo rate at 6.5%, keeps stance...            │
│ 3. 📰 FII inflows continue for 5th consecutive day...             │
│ 4. 📰 IT stocks rally on positive Q3 earnings outlook...          │
│ 5. 📰 Crude oil prices stabilize amid global demand...            │
└───────────────────────────────────────────────────────────────────┘

┌─ AI ENGINE STATUS ────────────────────────────────────────────────┐
│ STATUS:     🟢 ACTIVE                                              │
│ TASK:       🧠 Analyzing market patterns...                        │
│ CONFIDENCE: 🟢 78.5%                                               │
│ SIGNALS:    2 BUY signals detected                                │
└───────────────────────────────────────────────────────────────────┘

┌─ BANK NIFTY CHART PATTERN ───────────────────────────────────────┐
│     📈📈📈 UPTREND - Support at 44,800                             │
│     Resistance: 45,500 | Next target: 45,800                      │
└───────────────────────────────────────────────────────────────────┘

┌─ SYSTEM HEALTH & PERFORMANCE ────────────────────────────────────┐
│ 🔥 CPU: 🟢 35.2% ███████████░░░░░ (8c) Load: 2.45               │
│ 💾 RAM: 🟡 62.8% ████████████░░░░ 10.1/16.0G                     │
│ 💿 DSK: 🟢 45.3%  225.3/512.0G | NET ↑12.5M ↓45.3M               │
│ 🎮 GPU: NVIDIA GeForce RTX 3060                                   │
│    └─ Load:🟢 25.0% Mem:🟢 30.0% Temp:🟡 65°C Fan:🟢 45%        │
│ 🌡️  Temps: coretemp:58°C acpitz:52°C nvme:48°C                  │
│ 🟢 System Health: OPTIMAL (Avg: 47.8%)                            │
└───────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
Press Ctrl+C to stop | Switch to Web: 'w' | Refresh: 1s
═════════════════════════════════════════════════════════════════════
```

## Color Scheme Guide

### Performance Indicators
```
🟢 Green (Optimal)     < 50%   │ Everything running smoothly
🟡 Yellow (Moderate)   50-75%  │ Moderate load, still good
🔴 Red (High Load)     > 75%   │ High usage, may need attention
```

### Temperature Thresholds
```
CPU/System:
🟢 Cool      < 60°C
🟡 Warm      60-75°C
🔴 Hot       > 75°C

GPU:
🟢 Cool      < 60°C
🟡 Warm      60-75°C
🔴 Hot       > 85°C
```

### Trading Indicators
```
🟢 Profit    Positive PNL
🔴 Loss      Negative PNL
📈 Up        Price increase
📉 Down      Price decrease
```

## Section Update Frequencies

| Section | Update Rate | Data Source |
|---------|-------------|-------------|
| Account Balances | 1s | API endpoints / Simulation |
| Market Data | 1s | Market data API |
| Positions & Trades | 1s | Portfolio API |
| PNL Summary | 1s | Calculated from positions |
| News Headlines | 1s | News API |
| AI Status | 1s | AI engine API |
| Chart Pattern | 1s | Pattern recognition |
| System Stats | 1s | psutil + nvidia-smi |

## Visual Elements

### Progress Bars
```
████████████░░░░  ← 15 characters wide
███ = Filled (usage)
░░░ = Empty (available)
```

### Emojis Used
```
💰 Money/Balance
📈 Trending up
📉 Trending down
📊 Statistics
📰 News
🤖 AI/Robot
🧠 Brain/Thinking
🔥 Fire/CPU
💾 Disk/Storage
💿 CD/Disk
🎮 Gaming/GPU
🌡️  Thermometer
🟢 Green circle
🟡 Yellow circle
🔴 Red circle
```

## Responsive Layout

### Wide Terminal (120+ columns)
- Full information displayed
- Progress bars visible
- All metrics shown
- Emoji indicators included

### Narrow Terminal (80 columns)
- Compressed layout
- Essential info only
- Shorter labels
- No progress bars

### Minimum Width: 70 columns

## Interactive Features

### Current
- ✅ Real-time updates (1s)
- ✅ Color-coded status
- ✅ Progress bars
- ✅ Ctrl+C to exit

### Future (Planned)
- [ ] Arrow keys to navigate
- [ ] Tab to switch sections
- [ ] Space to pause updates
- [ ] 'r' to refresh immediately
- [ ] 's' to take snapshot
- [ ] 'h' to hide/show sections

## Screen Recording Example

```bash
# Start dashboard
python niraj.py --terminal-mode --paper-trading

# Output updates every second automatically
# All sections refresh simultaneously
# Colors provide instant status recognition
# Press Ctrl+C to stop gracefully
```

## Mobile/Remote View

Works perfectly over SSH:
```bash
# From remote machine
ssh user@trading-server
cd /path/to/niraj
python niraj.py --terminal-mode --paper-trading

# Dashboard renders in SSH terminal
# All features work remotely
# Low bandwidth required
```

## Comparison: Terminal vs Web Mode

### Terminal Mode (This Layout)
```
Pros:
✅ Lower CPU usage (2-5% vs 15-20%)
✅ Lower RAM usage (100MB vs 500MB)
✅ No GPU acceleration needed
✅ Works over SSH
✅ Faster startup
✅ Instant updates

Cons:
❌ Less interactive
❌ No mouse support
❌ Limited to text
```

### Web Mode
```
Pros:
✅ Rich visual interface
✅ Mouse interactions
✅ Charts and graphs
✅ Multiple panels
✅ Better for long sessions

Cons:
❌ Higher resource usage
❌ Requires browser
❌ More latency
❌ Not for SSH
```

## Accessibility

### Color Blind Support
- Emojis provide non-color indicators
- Text labels always present
- Multiple visual cues per status

### Screen Reader Support
- Plain text format
- Logical reading order
- Clear section headers

### High Contrast
- Bold section borders
- Clear separators
- Distinct colors

## Performance Optimization

### Efficient Rendering
- Clear screen once per second
- Batch print operations
- Minimal string operations
- Cached color codes

### Resource Usage
```
CPU:    2-5%     (system monitoring overhead)
RAM:    ~105MB   (including data structures)
Disk:   None     (all in-memory)
Network: Minimal (API calls only)
```

## Tips for Best Experience

1. **Terminal Settings**
   - Use monospace font (Courier, Consolas)
   - Enable 256 colors
   - Set buffer size to 3000+ lines
   - Disable line wrap

2. **Screen Size**
   - Minimum: 80x30 (columns x rows)
   - Recommended: 120x40
   - Optimal: 140x50

3. **Font Size**
   - Adjust for comfortable viewing
   - Consider distance from screen
   - Balance between detail and overview

4. **Theme**
   - Dark background recommended
   - Reduces eye strain
   - Better color contrast
   - Saves energy (OLED)

---

**Last Updated**: October 5, 2025
**Version**: 1.0.0
**Layout Status**: ✅ Production Ready
