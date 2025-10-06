# 🌀 GPU Fan Control Manual

## Overview

The NIRAJ Trading System now includes **independent manual GPU fan control** accessible directly from the main menu. This feature allows you to control NVIDIA GPU fan speeds without starting any trading services.

---

## 🚀 Quick Access

### From Main Menu
```bash
python niraj.py
# Select: 17 (GPU Fan Control)
```

### Quick Options
- **Press 'M'** → MAX SPEED NOW! (Set fans to 100% immediately)
- **Press 'F'** → START CONTINUOUS MAX SPEED (Keeps fans at 100%)

---

## 📋 Menu Options

### Option M: 🚀 MAX SPEED NOW! (100%)
**What it does:**
- Immediately sets all GPU fans to 100% maximum speed
- One-time setting (may revert after driver updates)
- Perfect for quick cooling when needed

**When to use:**
- Before starting intensive tasks
- When GPU temperature is high
- Quick cooling burst needed

### Option F: 🔥 START CONTINUOUS MAX SPEED (Fix Mode)
**What it does:**
- Sets fans to 100% and maintains it continuously
- Checks every 5 seconds and reapplies if needed
- Prevents driver from reverting to automatic control
- Runs in background until manually stopped

**When to use:**
- Long trading sessions
- Extended GPU usage
- When you need guaranteed max cooling
- Prevent thermal throttling

### Other Options
1. **Set Fan Speed (One-time)** - Choose custom speed (10-100%)
2. **Start Continuous Fan Control** - Maintain custom speed
3. **Stop Fan Controller** - Stop continuous mode
4. **Show Fan Controller Status** - Check current settings
5. **Monitor GPU Temperature** - Real-time temperature monitoring
6. **Fan Control Information** - Help and diagnostics
7. **Reset to Automatic Control** - Return to driver control

---

## 💻 Requirements

### Required Tools
- **nvidia-smi** - GPU monitoring (usually pre-installed)
- **nvidia-settings** - Fan control (usually pre-installed)

### Check Installation
```bash
which nvidia-smi
which nvidia-settings
```

### Install if Missing
```bash
sudo apt update
sudo apt install nvidia-utils nvidia-settings
```

---

## 🖥️ Hardware Compatibility

### ✅ Supported Systems
- **Desktop PCs** with NVIDIA GPUs
- Most **tower workstations**
- Systems with unlocked BIOS settings

### ⚠️ Limited Support
- **Laptop GPUs** (like RTX 3050 Laptop GPU)
- OEM systems with locked BIOS
- Pre-built systems with manufacturer restrictions

### Why Laptops May Not Work
Many laptop manufacturers lock fan control in the BIOS for safety and warranty reasons. The commands will execute but may not affect actual fan speed.

---

## 🎯 Usage Examples

### Example 1: Quick Max Speed Before Trading
```bash
python niraj.py
# Select: 17
# Press: M
# Fans immediately set to 100%
```

### Example 2: Continuous Max Speed for Long Session
```bash
python niraj.py
# Select: 17
# Press: F
# Controller maintains 100% continuously
# Use option 3 to stop when done
```

### Example 3: Custom Speed
```bash
python niraj.py
# Select: 17
# Select: 1 (Set Fan Speed)
# Enter: 70
# Fans set to 70% (one-time)
```

### Example 4: Monitor Temperature
```bash
python niraj.py
# Select: 17
# Select: 5 (Monitor GPU Temperature)
# Real-time temperature display
# Press Ctrl+C to exit monitoring
```

---

## 🔧 Technical Details

### How It Works

**One-time Mode (Option M, Option 1):**
1. Enables manual fan control: `GPUFanControlState=1`
2. Sets target fan speed: `GPUTargetFanSpeed=X`
3. Command executes once
4. May revert after driver updates or system events

**Continuous Mode (Option F, Option 2):**
1. Enables manual fan control
2. Sets initial target speed
3. Background thread starts
4. Every 5 seconds (default):
   - Checks fan control state
   - Re-enables manual control if needed
   - Resets target speed
5. Continues until manually stopped

### Command Line Integration

You can also control fans via command line:

```bash
# Max speed from command line (dashboard mode)
python niraj.py --terminal-mode --paper-trading --fan-speed max

# Continuous fix mode
python niraj.py --terminal-mode --fan-speed 100 --fix-fan-speed

# Custom interval
python niraj.py --terminal-mode --fan-speed 70 --fix-fan-speed --fan-check-interval 3.0
```

---

## 🛡️ Safety Notes

### Important Warnings
1. **Monitor temperatures** - Max fans don't guarantee safe temps
2. **Check cooling** - Ensure fans physically spin
3. **Noise levels** - 100% can be very loud
4. **Hardware wear** - Continuous max speed increases wear
5. **System stability** - Some systems may become unstable

### Best Practices
- Start with monitoring (Option 5) to check baseline temps
- Use continuous mode only when needed
- Stop continuous mode when task is complete
- Allow automatic control during idle times
- Check fan controller status regularly (Option 4)

### When to Stop
- GPU temperature drops to safe levels (< 70°C)
- Intensive task is complete
- System is idle
- Excessive noise is problematic
- Before shutting down system

---

## 🐛 Troubleshooting

### Issue: "Failed to set fan speed"
**Cause:** Missing nvidia-settings or insufficient permissions
**Solution:**
```bash
# Check installation
which nvidia-settings

# Install if missing
sudo apt install nvidia-settings

# Test manually
nvidia-settings -a '[gpu:0]/GPUFanControlState=1'
```

### Issue: "Fan control not available"
**Cause:** Laptop GPU with locked BIOS
**Solution:** Unfortunately, not much can be done. Some alternatives:
- Use laptop cooling pads
- Elevate laptop for better airflow
- Clean fans and vents
- Update BIOS (may unlock fan control)
- Use manufacturer-specific tools

### Issue: Fans spin but speed doesn't change
**Cause:** BIOS-locked fan curve
**Solution:**
- Check BIOS settings for fan control options
- Look for "Fan Control" or "Smart Fan" settings
- Some systems require specific key combinations at boot

### Issue: Settings revert immediately
**Cause:** Driver or system daemon overriding settings
**Solution:**
- Use continuous mode (Option F) to fight back
- Stop conflicting fan control software
- Check for system fan control services

### Issue: "No targets match specification"
**Cause:** GPU index or fan index mismatch
**Solution:** The script auto-detects GPU count, but if issues persist:
```bash
# Check GPU count
nvidia-smi --list-gpus

# Manually test different indices
nvidia-settings -a '[gpu:0]/GPUFanControlState=1'
nvidia-settings -a '[gpu:1]/GPUFanControlState=1'
```

---

## 📊 Monitoring

### Check Current Status
```bash
# From menu
python niraj.py → 17 → 4

# Using nvidia-smi
nvidia-smi --query-gpu=fan.speed,temperature.gpu --format=csv
```

### Real-time Monitoring
```bash
# From menu
python niraj.py → 17 → 5

# Using watch command
watch -n 1 nvidia-smi
```

---

## 🔄 Restoring Automatic Control

### From Menu
```bash
python niraj.py
# Select: 17
# Select: 7 (Reset to Automatic Control)
```

### Manually
```bash
# Disable manual control
nvidia-settings -a '[gpu:0]/GPUFanControlState=0'
```

### Automatic Restoration
Automatic control is usually restored after:
- System reboot
- Driver reload
- Graphics session restart
- Stopping continuous controller

---

## 💡 Tips & Tricks

### 1. Pre-Trading Routine
```bash
python niraj.py
# 17 → M (Max speed)
# 3 → Status (Check services)
# 13 → Paper Trading (Start trading)
```

### 2. Monitoring While Trading
- Keep terminal open with Option 5 (Temperature Monitor)
- Use Option 4 to check controller status periodically

### 3. Optimal Settings
- **Light trading:** 50-70% fan speed
- **Active trading:** 70-100% fan speed
- **Idle/monitoring:** Automatic control

### 4. Noise Reduction
If 100% is too loud:
- Try 70% (usually effective)
- Use continuous mode at 70%
- Position system for better natural airflow

---

## 📝 Summary

### Quick Reference

| Action | Menu Path | Shortcut |
|--------|-----------|----------|
| Max Speed Now | 17 → M | Immediate 100% |
| Continuous Max | 17 → F | Maintains 100% |
| Custom Speed | 17 → 1 | Choose 10-100% |
| Stop Controller | 17 → 3 | Stop continuous |
| Check Status | 17 → 4 | View settings |
| Monitor Temp | 17 → 5 | Real-time |
| Reset Auto | 17 → 7 | Driver control |

---

## 🎓 Learn More

- **Main Documentation:** See `SYSTEM_MONITORING_FEATURES.md`
- **Trading Dashboard:** See `TRADING_DASHBOARD_README.md`
- **General Help:** See `README.md`

---

## ✨ Key Features

✅ **Independent** - Works without starting trading services
✅ **Manual Control** - Direct, immediate fan control
✅ **Continuous Mode** - Maintains settings automatically
✅ **Multiple Options** - One-time or persistent control
✅ **Status Monitoring** - Always know current state
✅ **Temperature Tracking** - Built-in temp monitoring
✅ **Easy Access** - Right from main menu
✅ **Safe Defaults** - Automatic control on exit

---

**Last Updated:** October 5, 2025
**Version:** NIRAJ v1.0
**GPU Support:** NVIDIA GPUs with nvidia-settings
