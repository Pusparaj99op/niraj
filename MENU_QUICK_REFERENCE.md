# 🎯 Main Menu Quick Reference

## Menu Structure at a Glance

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                      🤖 NIRAJ TRADING SYSTEM (X/Y Running)                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  📊 Monitoring & Status         ⚡ Quick Actions        🎮 System & Config    ║
║  ┌──────────────────────┐      ┌──────────────────┐   ┌───────────────────┐ ║
║  │ 1. View Services     │      │ 4. Install Deps  │   │ 9. Interactive    │ ║
║  │ 2. View Logs         │      │ 5. Start All     │   │    Shell          │ ║
║  │ 3. Enhanced Status   │      │ 6. Restart All   │   │ 10. Quick Actions │ ║
║  └──────────────────────┘      │ 7. Test APIs     │   │ 11. Advanced      │ ║
║                                 │ 8. Stop Services │   │     Service       │ ║
║                                 └──────────────────┘   │ 12. System        │ ║
║                                                        │     Diagnostics   │ ║
║                                                        └───────────────────┘ ║
║                                                                               ║
║  📈 Trading Modes               ⚙️ Advanced             🚪 Exit               ║
║  ┌──────────────────────┐      ┌──────────────────┐   ┌───────────────────┐ ║
║  │ 13. Paper Trading    │      │ 15. GPU &        │   │ 0. Exit           │ ║
║  │ 14. Real Trading ⚠️  │      │     System       │   └───────────────────┘ ║
║  └──────────────────────┘      │     Monitor      │                         ║
║                                 │ 16. Keyboard     │                         ║
║                                 │     Shortcuts    │                         ║
║                                 └──────────────────┘                         ║
║                                                                               ║
║  💡 Tip: Type 'help' for shortcuts | 'status' for quick check | 'clear' to   ║
║         refresh | Uptime: X hours Y minutes                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Quick Access Guide

### 📊 Need to Check Something?
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| Service status | `1` | List all services (running/stopped) |
| View logs | `2` | Real-time log monitoring |
| Full system info | `3` | Status + CPU/RAM/Disk stats |
| Quick status | Type `status` | Instant status check |

### ⚡ Need to Start/Stop?
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| Install packages | `4` | Install backend & frontend dependencies |
| Start everything | `5` | Launch all services (dev stack) |
| Restart all | `6` | Quick restart of running services |
| Run tests | `7` | Test all external APIs |
| Stop everything | `8` | Gracefully stop all services |

### 🎮 Need Advanced Features?
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| Python console | `9` | IPython shell with NIRAJ loaded |
| Quick shortcuts | `10` | Submenu with 8 common actions |
| Granular control | `11` | Start/stop individual services |
| Health check | `12` | System diagnostics & troubleshooting |

### 📈 Ready to Trade?
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| Practice trading | `13` | Paper trading mode (safe) |
| Real trading | `14` | Live trading mode (⚠️ DANGER) |

### ⚙️ Need System Info?
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| GPU monitoring | `15` | Real-time GPU/CPU/RAM dashboard |
| Help & tips | `16` | Keyboard shortcuts guide |

### 🚪 Exit
| What You Want | Press | What It Does |
|---------------|-------|--------------|
| Quit | `0` | Graceful shutdown |

## Command Shortcuts

Type these **anywhere** in the menu:

| Command | Effect |
|---------|--------|
| `help` | Shows keyboard shortcuts & tips |
| `status` | Quick status with system info |
| `clear` | Clears the terminal screen |

## Option 10: Quick Actions Submenu

When you press `10`, you get:

```
⚡ QUICK ACTIONS
═══════════════════════════════════════════════════════════════════════
  1. 🚀 Start Full Dev Stack (Backend+Frontend+Redis+Ollama)
  2. 🏭 Start Production Stack (Backend+Redis)
  3. 🔄 Restart All Running Services
  4. 🛑 Stop All Services
  5. 🗑️  Clear All Cache & Logs
  6. 📊 Open Paper Trading Dashboard
  7. 🧪 Run Full API Test Suite
  8. 💾 Backup Configuration
  0. ⬅️  Back to Main Menu
═══════════════════════════════════════════════════════════════════════
```

## Common Workflows

### 🚀 First Time Setup
```
Step 1: Check status               → Press 3
Step 2: Install dependencies       → Press 4
Step 3: Start all services         → Press 5
Step 4: Test APIs                  → Press 7
Step 5: Start paper trading        → Press 13
```

### 🔄 Daily Development
```
Step 1: Quick start                → Press 10 → 1
Step 2: Monitor system             → Press 15
Step 3: View logs if issues        → Press 2
Step 4: Stop when done             → Press 8
```

### 🧪 Testing & Debugging
```
Step 1: Start services             → Press 5
Step 2: Run diagnostics            → Press 12
Step 3: Test APIs                  → Press 7
Step 4: Check logs                 → Press 2
```

### 📊 Trading Session
```
Step 1: Check system health        → Press 3
Step 2: Start paper trading        → Press 13
Step 3: Monitor in real-time       → Dashboard opens automatically
Step 4: Check GPU/system           → Press 15 (separate terminal)
```

### 🛠️ Maintenance
```
Step 1: Stop all services          → Press 8
Step 2: Clear cache                → Press 10 → 5
Step 3: Backup config              → Press 10 → 8
Step 4: Restart all                → Press 6
```

## Status Indicators

### Service Count (Header)
```
(4/8 Running)  → 4 services running out of 8 total
(0/8 Running)  → Nothing running
(8/8 Running)  → Everything running
```

### Color Coding
- 🟢 **Green** (< 50%) - Healthy, low usage
- 🟡 **Yellow** (50-75%) - Warning, medium usage  
- 🔴 **Red** (> 75%) - Critical, high usage

## Keyboard Controls

| Key | Function |
|-----|----------|
| `0-16` | Select menu option |
| `Enter` | Confirm / Continue |
| `Ctrl+C` | Exit gracefully |
| Type `help` | Show shortcuts |
| Type `status` | Quick check |
| Type `clear` | Clear screen |

## Pro Tips 💡

### Performance
- Use **Option 15** to monitor GPU temperature during trading
- Check **Option 3** before starting services (prevent resource conflicts)
- Use **Option 10 → 5** to clear cache if system sluggish

### Safety
- Always test with **Option 13** (paper trading) first
- **Option 14** (real trading) requires confirmation
- Use **Option 7** to verify APIs before trading

### Efficiency
- **Option 10** is your friend - fastest way to common tasks
- Type `status` instead of navigating to Option 3 for quick checks
- Use **Option 6** for quick restart instead of stop→start

### Troubleshooting
- **Option 12** runs health checks if something's wrong
- **Option 2** shows logs for debugging
- **Option 11** for granular service control if one service fails

## Feature Highlights

### What's New in Menu 2.0
✅ Service status in header (X/Y Running)  
✅ 3 organized categories for easy navigation  
✅ 5 new options (6, 10, 11, 12, 15)  
✅ Command shortcuts (help, status, clear)  
✅ Enhanced status with system info (Option 3)  
✅ Quick actions submenu (Option 10)  
✅ Real-time GPU monitoring (Option 15)  
✅ Comprehensive help system (Option 16)  
✅ Wider 80-char layout for better readability  
✅ Color-coded sections with emoji indicators  

## Need Help?

| Question | Solution |
|----------|----------|
| What does option X do? | Press `16` for detailed guide |
| How do I check if services are running? | Press `1` or type `status` |
| How to restart everything? | Press `6` |
| Where are the logs? | Press `2` |
| How to clear cache? | Press `10` → `5` |
| How to test APIs? | Press `7` |
| How to monitor GPU? | Press `15` |
| How to backup config? | Press `10` → `8` |

## Visual Legend

| Symbol | Meaning |
|--------|---------|
| 📊 | Monitoring & Status |
| ⚡ | Quick Actions |
| 🎮 | System & Configuration |
| 📈 | Trading Modes |
| ⚙️ | Advanced Features |
| 🚪 | Exit |
| 🟢 | Healthy/Running |
| 🟡 | Warning/Medium |
| 🔴 | Critical/High |
| ⚠️ | Danger/Caution |
| 💡 | Tip/Information |

---

**Quick Reference Version**: 2.0.0  
**Last Updated**: December 2024  
**For full documentation**: See [MAIN_MENU_ENHANCEMENTS.md](MAIN_MENU_ENHANCEMENTS.md)
