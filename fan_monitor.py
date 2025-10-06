#!/usr/bin/env python3
"""
Simple Terminal Fan Monitor for NIRAJ Trading System
Shows real-time temperature and system status
Fans are automatically controlled by laptop BIOS/ACPI
"""

import subprocess
import time
import sys
import os

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_temps():
    """Get current temperatures"""
    temps = {
        'cpu': 0,
        'gpu_amd': 0,
        'gpu_nvidia': 0,
        'nvme1': 0,
        'nvme2': 0,
        'acpi': 0
    }

    try:
        result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
        lines = result.stdout.split('\n')

        for line in lines:
            if 'Tctl:' in line or 'Tdie:' in line:  # CPU (AMD)
                temps['cpu'] = float(line.split('+')[1].split('°')[0])
            elif 'edge:' in line and 'amdgpu' in '\n'.join(lines[:lines.index(line)]):  # AMD GPU
                temps['gpu_amd'] = float(line.split('+')[1].split('°')[0])
            elif 'Composite:' in line:  # NVMe
                temp_val = float(line.split('+')[1].split('°')[0])
                if temps['nvme1'] == 0:
                    temps['nvme1'] = temp_val
                else:
                    temps['nvme2'] = temp_val
            elif 'temp1:' in line and 'acpitz' in '\n'.join(lines[:lines.index(line)]):  # ACPI temp
                temps['acpi'] = float(line.split('+')[1].split('°')[0])
    except:
        pass

    # Get NVIDIA GPU temp
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            temps['gpu_nvidia'] = float(result.stdout.strip())
    except:
        pass

    return temps

def get_status_icon(temp, thresholds):
    """Get status icon based on temperature"""
    if temp < thresholds[0]:
        return '🟢', 'COOL'
    elif temp < thresholds[1]:
        return '🟡', 'WARM'
    elif temp < thresholds[2]:
        return '🟠', 'HOT'
    else:
        return '🔴', 'CRITICAL'

def main():
    """Main monitoring loop"""
    print("Starting Fan Monitor...")
    print("Press Ctrl+C to exit")
    time.sleep(1)

    try:
        while True:
            clear_screen()
            temps = get_temps()

            print("╔═══════════════════════════════════════════════════════════╗")
            print("║        NIRAJ SYSTEM TEMPERATURE MONITOR                   ║")
            print("║        (Fans automatically controlled by BIOS)            ║")
            print("╚═══════════════════════════════════════════════════════════╝")
            print()

            # CPU
            icon, status = get_status_icon(temps['cpu'], [60, 75, 85])
            print(f"  CPU (AMD):       {icon} {temps['cpu']:>5.1f}°C  [{status}]")

            # AMD GPU
            if temps['gpu_amd'] > 0:
                icon, status = get_status_icon(temps['gpu_amd'], [60, 75, 85])
                print(f"  GPU (AMD):       {icon} {temps['gpu_amd']:>5.1f}°C  [{status}]")

            # NVIDIA GPU
            if temps['gpu_nvidia'] > 0:
                icon, status = get_status_icon(temps['gpu_nvidia'], [60, 75, 85])
                print(f"  GPU (NVIDIA):    {icon} {temps['gpu_nvidia']:>5.1f}°C  [{status}]")

            # NVMe
            if temps['nvme1'] > 0:
                icon, status = get_status_icon(temps['nvme1'], [50, 65, 75])
                print(f"  NVMe Drive 1:    {icon} {temps['nvme1']:>5.1f}°C  [{status}]")

            if temps['nvme2'] > 0:
                icon, status = get_status_icon(temps['nvme2'], [50, 65, 75])
                print(f"  NVMe Drive 2:    {icon} {temps['nvme2']:>5.1f}°C  [{status}]")

            # ACPI
            if temps['acpi'] > 0:
                icon, status = get_status_icon(temps['acpi'], [60, 75, 85])
                print(f"  System (ACPI):   {icon} {temps['acpi']:>5.1f}°C  [{status}]")

            print()
            print("═" * 61)
            print("  Status Guide:")
            print("    🟢 COOL     < 60°C  | Normal operation")
            print("    🟡 WARM   60-75°C  | Expected under load")
            print("    🟠 HOT    75-85°C  | Fans should spin up")
            print("    🔴 CRITICAL > 85°C  | Reduce load immediately")
            print("═" * 61)
            print()
            print(f"  Updated: {time.strftime('%H:%M:%S')}")
            print("  Press Ctrl+C to exit")

            # Check for critical temps
            max_temp = max(temps['cpu'], temps['gpu_amd'], temps['gpu_nvidia'], temps['acpi'])
            if max_temp > 85:
                print()
                print("  ⚠️  WARNING: High temperature detected!")
                print("     Laptop fans should be spinning at high speed.")
                print("     Consider: Cooling pad, clean vents, reduce load.")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
