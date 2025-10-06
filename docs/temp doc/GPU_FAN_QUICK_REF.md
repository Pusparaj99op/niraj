# 🌀 GPU Fan Control - Quick Reference Card

## 🚀 INSTANT MAX SPEED

```bash
python niraj.py
17    # GPU Fan Control
M     # MAX SPEED NOW!
```

**Result:** Fans immediately set to 100%

---

## 🔥 CONTINUOUS MAX SPEED

```bash
python niraj.py
17    # GPU Fan Control
F     # CONTINUOUS MAX (Fix Mode)
```

**Result:** Fans stay at 100% continuously

---

## 🎯 Quick Commands

| Key | Action | Description |
|-----|--------|-------------|
| **M** | **MAX NOW** | Immediate 100% (one-time) |
| **F** | **FIX MAX** | Continuous 100% (maintains) |
| 1 | Custom | Choose 10-100% (one-time) |
| 2 | Custom Fix | Choose 10-100% (continuous) |
| 3 | Stop | Stop continuous controller |
| 4 | Status | Check current settings |
| 5 | Monitor | Watch GPU temperature |
| 6 | Info | Help & diagnostics |
| 7 | Reset | Return to automatic |
| 0 | Back | Main menu |

---

## 📍 Menu Path

```
Main Menu
  └─ 17. GPU Fan Control
      ├─ M. MAX SPEED NOW!
      └─ F. CONTINUOUS MAX SPEED
```

---

## ⚡ Command Line Options

```bash
# One-time max speed
python niraj.py --terminal-mode --fan-speed max

# Continuous max speed
python niraj.py --terminal-mode --fan-speed 100 --fix-fan-speed

# Custom speed continuous
python niraj.py --terminal-mode --fan-speed 70 --fix-fan-speed
```

---

## ⚠️ Remember

- **M** = Quick blast (one-time)
- **F** = Keep it going (continuous)
- **3** = Stop continuous mode
- **4** = Check status
- **7** = Back to auto

---

## 💡 Tips

✅ Use **M** before heavy tasks
✅ Use **F** for long sessions
✅ Use **3** to stop when done
✅ Use **4** to verify status
✅ Use **5** to watch temps

---

## 🎮 Current System

**GPU:** RTX 3050 Laptop GPU
**Status:** BIOS Locked ⚠️
**Tools:** nvidia-smi ✅, nvidia-settings ✅

**Note:** Commands work but laptop BIOS may block actual fan control. Desktop GPUs work fully.

---

## 📚 Full Documentation

See `GPU_FAN_CONTROL_MANUAL.md` for complete guide.

---

**Quick Access:** `python niraj.py` → `17` → `M` or `F`
