#!/usr/bin/env python3
"""Quick test script for GPU fan control functionality"""

import sys
import subprocess
import shutil


def check_nvidia_tools():
    """Check if NVIDIA tools are available"""
    print("🔍 Checking NVIDIA Tools...")
    print("=" * 70)

    tools = {
        "nvidia-smi": shutil.which('nvidia-smi'),
        "nvidia-settings": shutil.which('nvidia-settings')
    }

    for tool, path in tools.items():
        if path:
            print(f"✅ {tool}: {path}")
        else:
            print(f"❌ {tool}: NOT FOUND")

    return all(tools.values())

def get_gpu_info():
    """Get GPU information"""
    print("\n📊 GPU Information:")
    print("=" * 70)

    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,temperature.gpu,fan.speed',
             '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                parts = line.split(', ')
                if len(parts) >= 4:
                    print(f"\nGPU {i}:")
                    print(f"  Name: {parts[0]}")
                    print(f"  Driver: {parts[1]}")
                    print(f"  Temperature: {parts[2]}")
                    print(f"  Fan Speed: {parts[3]}")
                else:
                    print(f"GPU {i}: {line}")
            return True
        else:
            print("❌ Failed to get GPU info")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False




def test_fan_control():
    """Test fan control availability"""
    print("\n🌀 Testing Fan Control:")
    print("=" * 70)

    try:
        # Test enabling manual fan control
        result = subprocess.run(
            ['nvidia-settings', '-a', '[gpu:0]/GPUFanControlState=1'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print("✅ Fan control enabled successfully")
            print(f"Output: {result.stdout.strip()}")

            # Test setting fan speed
            result = subprocess.run(
                ['nvidia-settings', '-a', '[fan:0]/GPUTargetFanSpeed=50'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print("✅ Fan speed set to 50% successfully")
                print(f"Output: {result.stdout.strip()}")
                return True
            else:
                print("⚠️  Fan speed setting returned error")
                print(f"Error: {result.stderr.strip()}")
                return False
        else:
            print("⚠️  Fan control enable returned error")
            print(f"Error: {result.stderr.strip()}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main test function"""
    print("\n🧪 GPU FAN CONTROL TEST")
    print("=" * 70)
    print()

    if not check_nvidia_tools():
        print("\n❌ Missing NVIDIA tools. Install with:")
        print("   sudo apt update")
        print("   sudo apt install nvidia-utils nvidia-settings")
        return 1

    if not get_gpu_info():
        print("\n⚠️  Could not retrieve GPU information")
        print("   Make sure you have NVIDIA GPU and drivers installed")
        return 1

    if not test_fan_control():
        print("\n⚠️  Fan control test did not complete successfully")
        print("\n💡 Note:")
        print("   • Some laptops have locked fan control via BIOS")
        print("   • Desktop systems usually support manual fan control")
        print("   • You may need to run with appropriate permissions")
        return 1

    print("\n" + "=" * 70)
    print("✅ All tests passed! Fan control is available.")
    print("=" * 70)
    print()
    print("💡 You can now use GPU fan control from the main menu:")
    print("   python niraj.py")
    print("   → Select option 17 (GPU Fan Control)")
    print("   → Press 'M' for MAX SPEED NOW")
    print("   → Press 'F' for CONTINUOUS MAX SPEED")
    print("   → Press '8' to run the unlock helper if fan control is locked")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
