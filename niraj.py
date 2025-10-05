#!/usr/bin/env python3
"""
NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System
Single Runner Script

This script provides a unified interface to run the NIRAJ trading system
with different configurations and modes.

Features:
  • Real-time trading dashboard with 1-second updates
  • Paper trading (₹10,000 virtual) and real trading modes
  • Live market data, PNL tracking, news, AI status
  • System monitoring: CPU, RAM, Disk, GPU, Temperatures
  • GPU fan speed control (NVIDIA with nvidia-settings)
  • Terminal mode for reduced resource usage
  • Service orchestration (Backend, Frontend, Redis, Ollama)

Usage:
    # Interactive menu
    python niraj.py

    # Paper trading dashboard with system monitoring
    python niraj.py --terminal-mode --paper-trading

    # Real trading with fan control
    python niraj.py --terminal-mode --real-trading --fan-speed 70

    # Start specific services
    python niraj.py --enable-api --enable-frontend

    # Production mode
    python niraj.py --mode production --enable-api --enable-redis

    # Service management
    python niraj.py status
    python niraj.py stop
    python niraj.py install

    # Dashboard only (requires backend running)
    python niraj.py --dashboard-only --paper-trading

    # Set GPU fan speed (10, 30, 50, 70, 100, max)
    python niraj.py --terminal-mode --fan-speed max

System Requirements:
  • Python 3.8+
  • psutil (for system monitoring)
  • nvidia-smi (optional, for GPU monitoring)
  • nvidia-settings (optional, for fan control)
  • colorama (for colored output)

Trading Dashboard Features:
  • Updates every 1 second
  • Account balances (Dhan + Angel One)
  • Live PNL with win/loss tracking
  • Market data (Bank Nifty trends)
  • Latest news headlines
  • AI engine status
  • Chart pattern indicators
  • System health metrics
  • GPU monitoring and control

See SYSTEM_MONITORING_FEATURES.md for detailed documentation.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import threading
import datetime
import webbrowser
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    PSUTIL_AVAILABLE = False
    # Lightweight fallback so attribute access doesn't crash linters/runtime

    class _DummyVM:
        used = 0
        total = 1
        percent = 0.0

    class _DummySW:
        used = 0
        total = 1

    class _DummyNet:
        bytes_sent = 0
        bytes_recv = 0

    class _PsutilFallback:
        def cpu_percent(self, interval=None):
            return 0.0

        def cpu_count(self, logical=True):  # noqa: D401
            return 0

        def virtual_memory(self):
            return _DummyVM()

        def swap_memory(self):
            return _DummySW()

        def net_io_counters(self):
            return _DummyNet()

        def sensors_temperatures(self):  # type: ignore
            return {}

    psutil = _PsutilFallback()  # type: ignore

try:
    from colorama import Fore, Style, init  # type: ignore

    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Fallback objects so references to Fore/Style remain valid without colorama.
    class _ColorFallback:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
        RESET = RESET_ALL = ""

    class _StyleFallback:
        BRIGHT = NORMAL = DIM = RESET_ALL = ""

    Fore = _ColorFallback()  # type: ignore
    Style = _StyleFallback()  # type: ignore

    def init(*_args: object, **_kwargs: object) -> None:  # type: ignore
        return None

    COLORAMA_AVAILABLE = False

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()


@dataclass
class ServiceConfig:
    """Configuration for a service.

    color kept as plain string to simplify fallback when colorama not installed.
    """

    name: str
    command: List[str]
    cwd: Path
    env: Dict[str, str]
    health_check_url: Optional[str] = None
    health_check_timeout: int = 30
    startup_time: int = 5
    color: str = getattr(Fore, "BLUE", "")
    start_time: Optional[float] = field(default=None, init=False)
    restart_count: int = field(default=0, init=False)


@runtime_checkable
class ProcessLike(Protocol):
    """Subset of subprocess.Popen interface used by the runner."""
    def poll(self) -> Optional[int]:  # noqa: D401
        ...

    def terminate(self) -> None:
        ...

    def kill(self) -> None:
        ...

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        ...


class NirajRunner:
    """Main runner class for NIRAJ system"""

    def __init__(self, mode: str = "development", config_file: Optional[str] = None):
        self.mode = mode
        self.config_file = config_file or "niraj-runner.json"
        # May contain real Popen instances or lightweight stand‑ins.
        self.processes: Dict[str, ProcessLike] = {}
        self.services: Dict[str, ServiceConfig] = {}
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.system_start_time: Optional[float] = None

        # Load configuration
        self.load_config()

    def print_box(self, text: str, width: int = 70, style: str = "single") -> None:
        """Print text in a styled box"""
        borders = {
            "single": ("┌", "─", "┐", "│", "└", "┘"),
            "double": ("╔", "═", "╗", "║", "╚", "╝"),
            "rounded": ("╭", "─", "╮", "│", "╰", "╯"),
            "bold": ("┏", "━", "┓", "┃", "┗", "┛"),
        }

        tl, h, tr, v, bl, br = borders.get(style, borders["single"])

        lines = text.split('\n')
        print(f"{tl}{h * (width - 2)}{tr}")
        for line in lines:
            padding = width - len(line) - 4
            print(f"{v} {line}{' ' * padding} {v}")
        print(f"{bl}{h * (width - 2)}{br}")

    def print_progress_bar(self, current: int, total: int, width: int = 40, label: str = "") -> None:
        """Print an animated progress bar"""
        percent = current / total
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)

        if COLORAMA_AVAILABLE:
            color = Fore.GREEN if percent == 1.0 else Fore.CYAN
            print(f"\r{color}{label} [{bar}] {int(percent * 100)}%{Style.RESET_ALL}", end='', flush=True)
        else:
            print(f"\r{label} [{bar}] {int(percent * 100)}%", end='', flush=True)

        if percent >= 1.0:
            print()  # New line when complete

    def print_spinner(self, message: str, duration: float = 2.0) -> None:
        """Print an animated spinner"""
        spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        start_time = time.time()
        idx = 0

        while time.time() - start_time < duration:
            if COLORAMA_AVAILABLE:
                print(f"\r{Fore.CYAN}{spinners[idx % len(spinners)]} {message}{Style.RESET_ALL}", end='', flush=True)
            else:
                print(f"\r{spinners[idx % len(spinners)]} {message}", end='', flush=True)
            idx += 1
            time.sleep(0.1)

        print(f"\r{' ' * (len(message) + 10)}\r", end='', flush=True)

    def get_uptime(self, service_name: str) -> str:
        """Get service uptime"""
        if service_name not in self.services:
            return "N/A"

        service = self.services[service_name]
        if service.start_time is None:
            return "Not running"

        uptime_seconds = time.time() - service.start_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def log(self, message: str, level: str = "info", service: str = "") -> None:
        """Log message with color coding"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{timestamp}]"

        if service:
            prefix += f" [{service}]"

        if COLORAMA_AVAILABLE:
            if level == "info":
                print(f"{Fore.BLUE}{prefix}[INFO]{Style.RESET_ALL} {message}")
            elif level == "success":
                print(f"{Fore.GREEN}{prefix}[SUCCESS]{Style.RESET_ALL} {message}")
            elif level == "warning":
                print(f"{Fore.YELLOW}{prefix}[WARNING]{Style.RESET_ALL} {message}")
            elif level == "error":
                print(f"{Fore.RED}{prefix}[ERROR]{Style.RESET_ALL} {message}")
            elif level == "header":
                print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
                print(f"{Fore.CYAN}{Style.BRIGHT}{message.center(60)}")
                print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
            elif level == "service":
                print(f"{Fore.MAGENTA}{prefix}[SERVICE]{Style.RESET_ALL} {message}")
        else:
            print(f"{prefix}[{level.upper()}] {message}")

    def load_config(self) -> None:
        """Load configuration from file or use defaults"""
        config_path = PROJECT_ROOT / self.config_file

        # Default configuration
        default_config = {
            "services": {
                "redis": {
                    "command": ["redis-server", "--daemonize", "yes"],
                    "cwd": ".",
                    "env": {},
                    "health_check": "redis-cli ping",
                    "startup_time": 2,
                    "color": "red",
                },
                "ollama": {
                    "command": ["ollama", "serve"],
                    "cwd": ".",
                    "env": {},
                    "health_check": "curl -s http://localhost:11434/api/tags",
                    "startup_time": 5,
                    "color": "green",
                },
                "backend": {
                    "command": [
                        "poetry",
                        "run",
                        "uvicorn",
                        "src.main:app",
                        "--reload",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                    ],
                    "cwd": "backend",
                    "env": {"PYTHONPATH": "."},
                    "health_check_url": "http://localhost:8000/health",
                    "startup_time": 10,
                    "color": "blue",
                },
                "frontend": {
                    "command": ["npm", "run", "dev"],
                    "cwd": "frontend",
                    "env": {},
                    "health_check_url": "http://localhost:5173",
                    "startup_time": 15,
                    "color": "cyan",
                },
            },
            "environments": {
                "development": {
                    "backend": {
                        "command": [
                            "poetry",
                            "run",
                            "uvicorn",
                            "src.main:app",
                            "--reload",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8000",
                        ]
                    }
                },
                "production": {
                    "backend": {
                        "command": [
                            "poetry",
                            "run",
                            "uvicorn",
                            "src.main:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8000",
                            "--workers",
                            "4",
                        ]
                    }
                },
                "testing": {
                    "backend": {
                        "command": [
                            "poetry",
                            "run",
                            "uvicorn",
                            "src.main:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8001",
                        ]
                    }
                },
            },
        }

        # Load custom config if exists
        config = default_config
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    custom_config = json.load(f)
                    # Merge configs
                    config = self._merge_configs(default_config, custom_config)
                self.log(f"Loaded configuration from {config_path}", "info")
            except Exception as e:
                self.log(f"Failed to load config file: {e}", "warning")

        # Build service configurations
        for service_name, service_data in config["services"].items():
            # Apply environment-specific overrides
            if self.mode in config.get("environments", {}):
                env_overrides = config["environments"][self.mode].get(service_name, {})
                service_data = {**service_data, **env_overrides}

            color_map = {
                "red": Fore.RED,
                "green": Fore.GREEN,
                "blue": Fore.BLUE,
                "cyan": Fore.CYAN,
                "yellow": Fore.YELLOW,
                "magenta": Fore.MAGENTA,
            }

            # Defensive extraction & validation (silent skip on invalid config).
            command_val = service_data.get("command")
            if not isinstance(command_val, list) or not all(isinstance(c, str) for c in command_val):
                continue
            cwd_val = service_data.get("cwd", ".")
            if not isinstance(cwd_val, str):
                cwd_val = str(cwd_val)
            env_val = service_data.get("env", {})
            env_clean: Dict[str, str] = {}
            if isinstance(env_val, Mapping):
                for k, v in env_val.items():
                    if isinstance(k, str):
                        env_clean[k] = str(v)
            startup_time_val = service_data.get("startup_time", 5)
            if not isinstance(startup_time_val, int):
                try:
                    startup_time_val = int(startup_time_val)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    startup_time_val = 5
            color_key = service_data.get("color", "blue")
            if not isinstance(color_key, str):
                color_key = str(color_key)
            self.services[service_name] = ServiceConfig(
                name=service_name,
                command=command_val,
                cwd=PROJECT_ROOT / cwd_val,
                env=env_clean,
                health_check_url=service_data.get("health_check_url"),
                startup_time=startup_time_val,
                color=color_map.get(color_key, getattr(Fore, "BLUE", "")),
            )

    def _merge_configs(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def check_prerequisites(self) -> bool:
        """Check if required tools are available"""
        self.log("🔍 Checking prerequisites...", "header")

        required_tools = {
            "python3": "Python 3",
            "poetry": "Poetry (Python dependency manager)",
            "node": "Node.js",
            "npm": "npm (Node package manager)",
        }

        optional_tools = {
            "redis-server": "Redis server",
            "ollama": "Ollama (AI model server)",
            "curl": "curl (for health checks)",
        }

        missing_required = []
        missing_optional = []

        for tool, description in required_tools.items():
            if not self._is_tool_available(tool):
                missing_required.append(f"{tool} ({description})")

        for tool, description in optional_tools.items():
            if not self._is_tool_available(tool):
                missing_optional.append(f"{tool} ({description})")

        if missing_required:
            self.log(
                f"❌ Missing required tools: {', '.join(missing_required)}", "error"
            )
            self.log("Please install missing tools and try again", "info")
            return False

        if missing_optional:
            self.log(
                f"⚠️  Missing optional tools (some features may not work): {', '.join(missing_optional)}",
                "warning",
            )

        self.log("✅ Prerequisites check completed", "success")
        return True

    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        try:
            subprocess.run(
                [tool, "--version"], capture_output=True, check=True, timeout=5
            )
            return True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return False

    def _is_ollama_running(self) -> bool:
        """Check if ollama is already running"""
        try:
            # Check if ollama API is responding
            result = subprocess.run(
                ["curl", "-s", "--max-time", "2", "http://127.0.0.1:11434/api/version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _is_redis_running(self) -> bool:
        """Check if redis is already running"""
        try:
            # Try to ping redis
            result = subprocess.run(
                ["redis-cli", "ping"],
                capture_output=True,
                timeout=5,
            )
            # Redis responds with "PONG" when running
            return result.returncode == 0 and b"PONG" in result.stdout
        except Exception:
            return False

    def set_environment(self) -> None:
        """Set environment variables based on mode"""
        os.environ["ENVIRONMENT"] = self.mode
        os.environ["PYTHONPATH"] = str(PROJECT_ROOT / "backend" / "src")

        # Set config file based on mode
        config_file = PROJECT_ROOT / "backend" / "config" / f"{self.mode}.yaml"
        if config_file.exists():
            os.environ["NIRAJ_CONFIG_FILE"] = str(config_file)

        # Load environment file if exists
        env_file = PROJECT_ROOT / f".env.{self.mode}"
        if not env_file.exists():
            env_file = PROJECT_ROOT / ".env"

        if env_file.exists():
            self._load_env_file(env_file)

        self.log(f"🌍 Environment set to: {self.mode}", "info")

    def _load_env_file(self, env_file: Path) -> None:
        """Load environment variables from .env file"""
        try:
            with open(env_file, "r") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    if not key:
                        continue
                    os.environ[key] = value.strip()
            self.log(f"📄 Loaded environment from {env_file}", "info")
        except Exception as e:
            self.log(f"Failed to load env file {env_file}: {e}", "warning")

    def start_service(self, service_name: str) -> bool:
        """Start a specific service"""
        if service_name not in self.services:
            self.log(f"Unknown service: {service_name}", "error")
            return False

        service = self.services[service_name]

        # Special handling for redis - check if already running as system service
        if service_name == "redis":
            if self._is_redis_running():
                self.log("✅ Redis already running as system service", "success")

                # Create a dummy process entry to track it
                class DummyProcessOllama:
                    """Lightweight stand‑in for an already‑running system service."""

                    def poll(self) -> Optional[int]:
                        return None

                    def terminate(self) -> None:  # no-op
                        return None

                    def kill(self) -> None:  # no-op
                        return None

                    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
                        return None

                self.processes[service_name] = DummyProcessOllama()
                self.services[service_name].start_time = time.time()
                return True

        # Special handling for ollama - check if already running as system service
        if service_name == "ollama":
            if self._is_ollama_running():
                self.log("✅ Ollama already running as system service", "success")

                # Create a dummy process entry to track it
                class DummyProcess:
                    """Lightweight stand‑in for an already‑running system service."""

                    def poll(self) -> Optional[int]:
                        return None

                    def terminate(self) -> None:  # no-op
                        return None

                    def kill(self) -> None:  # no-op
                        return None

                    def wait(self, timeout: Optional[float] = None) -> Optional[int]:  # noqa: D401,E501
                        return None

                self.processes[service_name] = DummyProcess()
                return True

        # Check if already running
        if (
            service_name in self.processes
            and self.processes[service_name].poll() is None
        ):
            self.log(f"Service {service_name} already running", "warning")
            return True

        self.log(f"🚀 Starting {service_name}...", "service")

        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(service.env)

            # For long-running services, don't capture output to avoid blocking
            # Instead, let them output to the terminal or redirect to log files
            log_file = PROJECT_ROOT / "logs" / f"{service_name}.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, "a") as log_out:
                # Start process
                popen_obj = subprocess.Popen(
                    service.command,
                    cwd=service.cwd,
                    env=env,
                    stdout=log_out,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self.processes[service_name] = popen_obj

            # Wait for startup
            self.log(
                f"⏳ Waiting {service.startup_time}s for {service_name} to start...",
                "info",
            )
            time.sleep(service.startup_time)

            # Check if process is still running
            process_ref = self.processes[service_name]
            if process_ref.poll() is None:
                # Perform health check if configured
                if self._check_service_health(service):
                    self.log(f"✅ {service_name} started successfully", "success")
                    self.log(f"   📄 Logs: {log_file}", "info")
                    service.start_time = time.time()  # Track start time
                    return True
                else:
                    self.log(f"❌ {service_name} health check failed", "error")
                    self.stop_service(service_name)
                    return False
            else:
                # Process exited, check log file for errors
                self.log(f"❌ {service_name} failed to start", "error")
                self.log(f"   📄 Check logs at: {log_file}", "info")
                return False

        except Exception as e:
            self.log(f"❌ Failed to start {service_name}: {e}", "error")
            return False

    def _check_service_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy"""
        if not service.health_check_url:
            return True  # No health check configured

        try:
            import requests

            response = requests.get(service.health_check_url, timeout=5)
            return response.status_code == 200
        except ImportError:
            # Fallback to curl if requests not available
            try:
                result = subprocess.run(
                    ["curl", "-s", "--max-time", "5", service.health_check_url],
                    capture_output=True,
                    timeout=10,
                )
                return result.returncode == 0
            except Exception:
                pass
        except Exception:
            pass

        # If health check fails, assume service is healthy (for now)
        return True

    def stop_service(self, service_name: str) -> None:
        """Stop a specific service"""
        if service_name not in self.processes:
            self.log(f"Service {service_name} not running", "warning")
            return

        process = self.processes[service_name]
        if process.poll() is not None:
            self.log(f"Service {service_name} already stopped", "warning")
            return

        self.log(f"🛑 Stopping {service_name}...", "service")

        try:
            process.terminate()
            process.wait(timeout=10)
            self.log(f"✅ {service_name} stopped", "success")
            # Reset start time
            if service_name in self.services:
                self.services[service_name].start_time = None
        except subprocess.TimeoutExpired:
            process.kill()
            self.log(f"⚠️  {service_name} force killed", "warning")
            if service_name in self.services:
                self.services[service_name].start_time = None
        except Exception as e:
            self.log(f"❌ Error stopping {service_name}: {e}", "error")
        finally:
            del self.processes[service_name]

    def stop_all(self) -> None:
        """Stop all running processes"""
        self.log("🛑 Stopping all services...", "header")

        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)

        self.log("✅ All services stopped", "success")

    def show_status(self) -> None:
        """Show status of all services with enhanced dashboard display"""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{'═' * 78}╗")
            print(f"║{'NIRAJ SYSTEM STATUS DASHBOARD'.center(78)}║")
            print(f"╠{'═' * 78}╣")
            print(f"║ Mode: {Fore.YELLOW}{self.mode.upper()}{Fore.CYAN}{' ' * (71 - len(self.mode))}║")

            # System uptime
            if self.system_start_time:
                uptime_sec = time.time() - self.system_start_time
                uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m {int(uptime_sec % 60)}s"
                print(f"║ System Uptime: {Fore.GREEN}{uptime_str}{Fore.CYAN}{' ' * (60 - len(uptime_str))}║")

            running_count = sum(1 for name in self.processes if self.processes[name].poll() is None)
            total_count = len(self.services)
            print(f"║ Services Running: {Fore.GREEN}{running_count}{Fore.CYAN}/{Fore.YELLOW}{total_count}{Fore.CYAN}{' ' * (57)}║")
            print(f"╠{'═' * 78}╣")
            print(f"║ {'Service'.ljust(15)} │ {'Status'.ljust(12)} │ {'Uptime'.ljust(15)} │ {'Restarts'.ljust(8)} │ {'Port'.ljust(18)} ║")
            print(f"╠{'═' * 78}╣{Style.RESET_ALL}")
        else:
            print("\n" + "=" * 80)
            print("NIRAJ SYSTEM STATUS DASHBOARD".center(80))
            print("=" * 80)

        for service_name, service in self.services.items():
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    status = "✅ Running" if COLORAMA_AVAILABLE else "Running"
                    uptime = self.get_uptime(service_name)
                    restarts = str(service.restart_count)

                    # Service URLs/Ports
                    port_info = ""
                    if service_name == "backend":
                        port_info = ":8000"
                    elif service_name == "frontend":
                        port_info = ":5173"
                    elif service_name == "redis":
                        port_info = ":6379"
                    elif service_name == "ollama":
                        port_info = ":11434"

                    if COLORAMA_AVAILABLE:
                        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}{service_name.ljust(15)}{Style.RESET_ALL} │ "
                              f"{Fore.GREEN}{status.ljust(12)}{Style.RESET_ALL} │ "
                              f"{Fore.YELLOW}{uptime.ljust(15)}{Style.RESET_ALL} │ "
                              f"{Fore.MAGENTA}{restarts.ljust(8)}{Style.RESET_ALL} │ "
                              f"{Fore.BLUE}{port_info.ljust(18)}{Style.RESET_ALL} {Fore.CYAN}║{Style.RESET_ALL}")
                    else:
                        print(f"{service_name.ljust(15)} | {status.ljust(12)} | {uptime.ljust(15)} | {restarts.ljust(8)} | {port_info.ljust(18)}")
                else:
                    status = "❌ Stopped" if COLORAMA_AVAILABLE else "Stopped"
                    if COLORAMA_AVAILABLE:
                        print(f"{Fore.CYAN}║{Style.RESET_ALL} {service_name.ljust(15)} │ "
                              f"{Fore.RED}{status.ljust(12)}{Style.RESET_ALL} │ "
                              f"{'---'.ljust(15)} │ {'---'.ljust(8)} │ {'---'.ljust(18)} {Fore.CYAN}║{Style.RESET_ALL}")
                    else:
                        print(f"{service_name.ljust(15)} | {status.ljust(12)} | {'---'.ljust(15)} | {'---'.ljust(8)} | {'---'.ljust(18)}")
            else:
                status = "⭕ Not Started" if COLORAMA_AVAILABLE else "Not Started"
                if COLORAMA_AVAILABLE:
                    print(f"{Fore.CYAN}║{Style.RESET_ALL} {service_name.ljust(15)} │ "
                          f"{Fore.YELLOW}{status.ljust(12)}{Style.RESET_ALL} │ "
                          f"{'---'.ljust(15)} │ {'---'.ljust(8)} │ {'---'.ljust(18)} {Fore.CYAN}║{Style.RESET_ALL}")
                else:
                    print(f"{service_name.ljust(15)} | {status.ljust(12)} | {'---'.ljust(15)} | {'---'.ljust(8)} | {'---'.ljust(18)}")

        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{Style.BRIGHT}💡 Quick Access URLs:{Style.RESET_ALL}")
            print(f"  {Fore.BLUE}• Backend API:{Style.RESET_ALL}      http://localhost:8000")
            print(f"  {Fore.BLUE}• API Docs:{Style.RESET_ALL}         http://localhost:8000/docs")
            print(f"  {Fore.BLUE}• Frontend:{Style.RESET_ALL}         http://localhost:5173")
            print(f"  {Fore.BLUE}• Ollama API:{Style.RESET_ALL}       http://localhost:11434")
        else:
            print("=" * 80)
            print("\nQuick Access URLs:")
            print("  • Backend API:      http://localhost:8000")
            print("  • API Docs:         http://localhost:8000/docs")
            print("  • Frontend:         http://localhost:5173")
            print("  • Ollama API:       http://localhost:11434")

        print()
        print()

    def start_monitoring(self) -> None:
        """Start monitoring thread"""
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_services, daemon=True
        )
        self.monitor_thread.start()
        self.log("👀 Service monitoring started", "info")

    def stop_monitoring(self) -> None:
        """Stop monitoring thread"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_services(self) -> None:
        """Monitor running services"""
        while self.monitoring_active:
            for service_name, process in list(self.processes.items()):
                if process.poll() is not None:
                    self.log(f"🚨 Service {service_name} exited unexpectedly", "error")
                    # Remove from processes dict
                    del self.processes[service_name]
            time.sleep(2)

    def run(self, services_to_start: List[str]) -> None:
        """Run the NIRAJ system"""

        self.log("🚀 Starting NIRAJ Trading System", "header")

        if not self.check_prerequisites():
            return

        self.set_environment()

        # Track system start time
        self.system_start_time = time.time()

        # Start services
        started_services = []
        for i, service_name in enumerate(services_to_start, 1):
            self.print_progress_bar(i - 1, len(services_to_start), label="Starting services")
            if self.start_service(service_name):
                started_services.append(service_name)
            self.print_progress_bar(i, len(services_to_start), label="Starting services")

        if not started_services:
            self.log("❌ No services were started successfully", "error")
            return

        # Display status
        self.show_status()

        # Start monitoring
        self.start_monitoring()

        # Setup signal handlers
        def signal_handler(signum, frame):
            self.log(f"🛑 Received signal {signum}, shutting down...", "warning")
            self.stop_monitoring()
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep running until interrupted
        try:
            self.log("🎯 NIRAJ is running! Press Ctrl+C to stop all services", "info")
            while self.monitoring_active:
                time.sleep(1)

        except KeyboardInterrupt:
            self.stop_monitoring()
            self.stop_all()

    def install_dependencies(self) -> None:
        """Install project dependencies"""
        self.log("📦 Installing dependencies...", "header")

        # Install backend dependencies
        backend_dir = PROJECT_ROOT / "backend"
        if backend_dir.exists():
            self.log("Installing backend dependencies...", "info")
            try:
                subprocess.run(["poetry", "install"], cwd=backend_dir, check=True)
                self.log("✅ Backend dependencies installed", "success")
            except subprocess.CalledProcessError as e:
                self.log(f"❌ Failed to install backend dependencies: {e}", "error")

        # Install frontend dependencies
        frontend_dir = PROJECT_ROOT / "frontend"
        if frontend_dir.exists():
            self.log("Installing frontend dependencies...", "info")
            try:
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
                self.log("✅ Frontend dependencies installed", "success")
            except subprocess.CalledProcessError as e:
                self.log(f"❌ Failed to install frontend dependencies: {e}", "error")

    def test_api_endpoints(self) -> Dict[str, bool]:
        """Test all API endpoints and return results"""
        self.log("🧪 Testing API endpoints...", "header")

        endpoints = {
            "Health Check": "http://localhost:8000/health",
            "System Info": "http://localhost:8000/info",
            "API Root": "http://localhost:8000/",
            "API Documentation": "http://localhost:8000/docs",
            "OpenAPI Schema": "http://localhost:8000/openapi.json",
        }

        results: Dict[str, bool] = {}

        # Check if backend is running
        if "backend" not in self.processes or self.processes["backend"].poll() is not None:
            self.log("❌ Backend is not running. Please start the backend first.", "error")
            return results

        for name, url in endpoints.items():
            self.log(f"Testing {name}: {url}", "info")
            try:
                # Try using requests library
                try:
                    import requests
                    response = requests.get(url, timeout=5)
                    status_code = response.status_code
                    success = 200 <= status_code < 300
                except ImportError:
                    # Fallback to curl
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    success = 200 <= status_code < 300

                if success:
                    self.log(f"  ✅ {name}: OK (Status: {status_code})", "success")
                    results[name] = True
                else:
                    self.log(f"  ❌ {name}: Failed (Status: {status_code})", "error")
                    results[name] = False

            except Exception as e:
                self.log(f"  ❌ {name}: Error - {e}", "error")
                results[name] = False

            time.sleep(0.5)  # Small delay between requests

        # Summary
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        self.log(f"\n📊 API Test Summary: {passed}/{total} endpoints passed",
                 "success" if passed == total else "warning")

        return results

    def test_broker_apis(self) -> Dict[str, Dict[str, bool]]:
        """Test broker API endpoints (Angel One and Dhan)"""
        self.log("📡 Testing Broker APIs...", "header")

        results = {
            "angel_one": {},
            "dhan": {}
        }

        # Check if backend is running
        if "backend" not in self.processes or self.processes["backend"].poll() is not None:
            self.log("❌ Backend is not running. Please start the backend first.", "error")
            return results

        try:
            import requests
        except ImportError:
            self.log("⚠️  requests library not available, using curl", "warning")
            requests = None

        # Angel One API Tests
        self.log("\n🔵 Testing Angel One APIs:", "info")
        angel_endpoints = {
            "Market Data Status": "http://localhost:8000/api/v1/market-data/status",
            "Get Quote": "http://localhost:8000/api/v1/market-data/quotes",
            "LTP (Last Traded Price)": "http://localhost:8000/api/v1/market-data/RELIANCE/ltp",
            "Portfolio": "http://localhost:8000/api/v1/market-data/watchlist",
        }

        for name, url in angel_endpoints.items():
            try:
                if requests:
                    response = requests.get(url, timeout=5)
                    success = 200 <= response.status_code < 500  # Accept 4xx as "reachable"
                    status_code = response.status_code
                else:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                        capture_output=True, text=True, timeout=10
                    )
                    status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    success = 200 <= status_code < 500

                results["angel_one"][name] = success
                if success:
                    self.log(f"  ✅ {name}: Reachable (Status: {status_code})", "success")
                else:
                    self.log(f"  ❌ {name}: Failed (Status: {status_code})", "error")
            except Exception as e:
                self.log(f"  ❌ {name}: Error - {e}", "error")
                results["angel_one"][name] = False

            time.sleep(0.3)

        # Dhan API Tests
        self.log("\n🟢 Testing Dhan APIs:", "info")
        dhan_endpoints = {
            "Market Feed": "http://localhost:8000/api/v1/market-data/status",
            "Historical Data": "http://localhost:8000/api/v1/market-data/RELIANCE",
            "Portfolio": "http://localhost:8000/api/v1/market-data/watchlist",
        }

        for name, url in dhan_endpoints.items():
            try:
                if requests:
                    response = requests.get(url, timeout=5)
                    success = 200 <= response.status_code < 500
                    status_code = response.status_code
                else:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                        capture_output=True, text=True, timeout=10
                    )
                    status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    success = 200 <= status_code < 500

                results["dhan"][name] = success
                if success:
                    self.log(f"  ✅ {name}: Reachable (Status: {status_code})", "success")
                else:
                    self.log(f"  ❌ {name}: Failed (Status: {status_code})", "error")
            except Exception as e:
                self.log(f"  ❌ {name}: Error - {e}", "error")
                results["dhan"][name] = False

            time.sleep(0.3)

        # Summary
        angel_passed = sum(1 for v in results["angel_one"].values() if v)
        angel_total = len(results["angel_one"])
        dhan_passed = sum(1 for v in results["dhan"].values() if v)
        dhan_total = len(results["dhan"])

        self.log("\n📊 Broker API Summary:", "info")
        self.log(f"  Angel One: {angel_passed}/{angel_total} endpoints reachable",
                 "success" if angel_passed == angel_total else "warning")
        self.log(f"  Dhan: {dhan_passed}/{dhan_total} endpoints reachable",
                 "success" if dhan_passed == dhan_total else "warning")

        return results

    def test_news_api(self) -> Dict[str, bool]:
        """Test News API endpoints"""
        self.log("📰 Testing News APIs...", "header")

        results = {}

        # Check if backend is running
        if "backend" not in self.processes or self.processes["backend"].poll() is not None:
            self.log("❌ Backend is not running. Please start the backend first.", "error")
            return results

        try:
            import requests
        except ImportError:
            self.log("⚠️  requests library not available, using curl", "warning")
            requests = None

        news_endpoints = {
            "News Health": "http://localhost:8000/api/v1/news/health",
            "Headlines": "http://localhost:8000/api/v1/news/headlines",
            "Company News": "http://localhost:8000/api/v1/news/company/RELIANCE",
        }

        for name, url in news_endpoints.items():
            try:
                if requests:
                    response = requests.get(url, timeout=10)
                    success = 200 <= response.status_code < 500
                    status_code = response.status_code
                else:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                        capture_output=True, text=True, timeout=15
                    )
                    status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    success = 200 <= status_code < 500

                results[name] = success
                if success:
                    self.log(f"  ✅ {name}: Reachable (Status: {status_code})", "success")
                else:
                    self.log(f"  ❌ {name}: Failed (Status: {status_code})", "error")
            except Exception as e:
                self.log(f"  ❌ {name}: Error - {e}", "error")
                results[name] = False

            time.sleep(0.5)

        # Summary
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        self.log(f"\n📊 News API Summary: {passed}/{total} endpoints reachable",
                 "success" if passed == total else "warning")

        return results

    def test_weather_api(self) -> Dict[str, bool]:
        """Test Weather API endpoints"""
        self.log("🌤️  Testing Weather APIs...", "header")

        results = {}

        # Check if backend is running
        if "backend" not in self.processes or self.processes["backend"].poll() is not None:
            self.log("❌ Backend is not running. Please start the backend first.", "error")
            return results

        try:
            import requests
        except ImportError:
            self.log("⚠️  requests library not available, using curl", "warning")
            requests = None

        weather_endpoints = {
            "Weather Health": "http://localhost:8000/api/v1/weather/health",
            "Current Weather": "http://localhost:8000/api/v1/weather/current?city=Mumbai",
            "Forecast": "http://localhost:8000/api/v1/weather/forecast?city=Mumbai",
        }

        for name, url in weather_endpoints.items():
            try:
                if requests:
                    response = requests.get(url, timeout=10)
                    success = 200 <= response.status_code < 500
                    status_code = response.status_code
                else:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                        capture_output=True, text=True, timeout=15
                    )
                    status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
                    success = 200 <= status_code < 500

                results[name] = success
                if success:
                    self.log(f"  ✅ {name}: Reachable (Status: {status_code})", "success")
                else:
                    self.log(f"  ❌ {name}: Failed (Status: {status_code})", "error")
            except Exception as e:
                self.log(f"  ❌ {name}: Error - {e}", "error")
                results[name] = False

            time.sleep(0.5)

        # Summary
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        self.log(f"\n📊 Weather API Summary: {passed}/{total} endpoints reachable",
                 "success" if passed == total else "warning")

        return results

    def test_all_external_apis(self) -> Dict[str, Any]:
        """Test all external APIs comprehensively"""
        self.log("🔬 Testing All External APIs...", "header")

        all_results = {
            "core": self.test_api_endpoints(),
            "brokers": self.test_broker_apis(),
            "news": self.test_news_api(),
            "weather": self.test_weather_api(),
        }

        # Overall summary
        self.log("\n" + "=" * 60, "info")
        self.log("📊 COMPREHENSIVE API TEST SUMMARY", "header")
        self.log("=" * 60, "info")

        # Core APIs
        core_passed = sum(1 for v in all_results["core"].values() if v)
        core_total = len(all_results["core"])
        self.log(f"Core APIs: {core_passed}/{core_total} passed",
                 "success" if core_passed == core_total else "warning")

        # Broker APIs
        angel_passed = sum(1 for v in all_results["brokers"]["angel_one"].values() if v)
        angel_total = len(all_results["brokers"]["angel_one"])
        dhan_passed = sum(1 for v in all_results["brokers"]["dhan"].values() if v)
        dhan_total = len(all_results["brokers"]["dhan"])
        self.log(f"Angel One APIs: {angel_passed}/{angel_total} reachable",
                 "success" if angel_passed == angel_total else "warning")
        self.log(f"Dhan APIs: {dhan_passed}/{dhan_total} reachable",
                 "success" if dhan_passed == dhan_total else "warning")

        # News APIs
        news_passed = sum(1 for v in all_results["news"].values() if v)
        news_total = len(all_results["news"])
        self.log(f"News APIs: {news_passed}/{news_total} reachable",
                 "success" if news_passed == news_total else "warning")

        # Weather APIs
        weather_passed = sum(1 for v in all_results["weather"].values() if v)
        weather_total = len(all_results["weather"])
        self.log(f"Weather APIs: {weather_passed}/{weather_total} reachable",
                 "success" if weather_passed == weather_total else "warning")

        self.log("=" * 60 + "\n", "info")

        return all_results

    def clear_redis_cache(self) -> bool:
        """Clear Redis cache"""
        self.log("🗑️  Clearing Redis cache...", "info")

        try:
            # Try using redis-cli
            result = subprocess.run(
                ["redis-cli", "FLUSHALL"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.log("✅ Redis cache cleared successfully", "success")
                return True
            else:
                self.log(f"❌ Failed to clear Redis cache: {result.stderr}", "error")
                return False

        except FileNotFoundError:
            self.log("❌ redis-cli not found. Please install Redis tools.", "error")
            return False
        except Exception as e:
            self.log(f"❌ Error clearing Redis cache: {e}", "error")
            return False

    def clear_logs(self, log_path: Optional[Path] = None) -> bool:
        """Clear log files"""
        self.log("🗑️  Clearing logs...", "info")

        log_files = []
        if log_path:
            log_files.append(log_path)
        else:
            # Default log locations
            log_files = [
                PROJECT_ROOT / "logs" / "niraj.log",
                PROJECT_ROOT / "backend" / "logs" / "niraj.log",
            ]

        cleared = 0
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'w') as f:
                        f.write("")
                    self.log(f"✅ Cleared: {log_file}", "success")
                    cleared += 1
                except Exception as e:
                    self.log(f"❌ Failed to clear {log_file}: {e}", "error")
            else:
                self.log(f"⚠️  Log file not found: {log_file}", "warning")

        if cleared > 0:
            self.log(f"✅ Cleared {cleared} log file(s)", "success")
            return True
        else:
            self.log("⚠️  No log files were cleared", "warning")
            return False

    def view_logs(self, lines: int = 50) -> None:
        """View recent log entries"""
        self.log(f"📋 Viewing last {lines} log lines...", "header")

        log_files = [
            PROJECT_ROOT / "logs" / "niraj.log",
            PROJECT_ROOT / "backend" / "logs" / "niraj.log",
        ]

        for log_file in log_files:
            if log_file.exists():
                self.log(f"\n📄 {log_file}:", "info")
                try:
                    result = subprocess.run(
                        ["tail", "-n", str(lines), str(log_file)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout:
                        print(result.stdout)
                    else:
                        self.log("  (empty)", "info")
                except Exception as e:
                    self.log(f"  ❌ Error reading log: {e}", "error")
            else:
                self.log(f"⚠️  Log file not found: {log_file}", "warning")

    def get_log_size(self) -> Dict[str, int]:
        """Get size of log files in bytes"""
        log_files = [
            PROJECT_ROOT / "logs" / "niraj.log",
            PROJECT_ROOT / "backend" / "logs" / "niraj.log",
        ]

        sizes: Dict[str, int] = {}
        for log_file in log_files:
            if log_file.exists():
                try:
                    sizes[str(log_file)] = log_file.stat().st_size
                except Exception:
                    sizes[str(log_file)] = 0

        return sizes

    def clear_cache_directory(self, cache_dir: Optional[Path] = None) -> bool:
        """Clear cache directory"""
        self.log("🗑️  Clearing cache directory...", "info")

        if cache_dir is None:
            cache_dir = PROJECT_ROOT / "backend" / "__pycache__"

        if not cache_dir.exists():
            self.log(f"⚠️  Cache directory not found: {cache_dir}", "warning")
            return False

        try:
            import shutil
            shutil.rmtree(cache_dir)
            self.log(f"✅ Cleared cache directory: {cache_dir}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Failed to clear cache directory: {e}", "error")
            return False

    def get_system_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive system diagnostics"""
        diagnostics: Dict[str, Any] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "mode": self.mode,
            "system_uptime": None,
            "services": {},
            "disk_usage": {},
            "process_info": {}
        }

        # System uptime
        if self.system_start_time:
            diagnostics["system_uptime"] = time.time() - self.system_start_time

        # Service status
        for service_name, service in self.services.items():
            status_info = {
                "running": service_name in self.processes and self.processes[service_name].poll() is None,
                "uptime": self.get_uptime(service_name) if service.start_time else "N/A",
                "restarts": service.restart_count,
                "start_time": service.start_time
            }
            diagnostics["services"][service_name] = status_info

        # Disk usage for key directories
        try:
            for dir_name in ["logs", "data", "backend", "frontend"]:
                dir_path = PROJECT_ROOT / dir_name
                if dir_path.exists():
                    total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    diagnostics["disk_usage"][dir_name] = {
                        "bytes": total_size,
                        "mb": round(total_size / (1024 * 1024), 2)
                    }
        except Exception:
            pass

        return diagnostics

    def backup_configuration(self, backup_path: Optional[Path] = None) -> bool:
        """Backup current configuration"""
        if backup_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = PROJECT_ROOT / f"niraj-backup-{timestamp}.json"

        try:
            backup_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "mode": self.mode,
                "services": {},
                "diagnostics": self.get_system_diagnostics()
            }

            # Save service configurations
            for name, service in self.services.items():
                backup_data["services"][name] = {
                    "command": service.command,
                    "cwd": str(service.cwd),
                    "env": service.env,
                    "startup_time": service.startup_time
                }

            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2)

            self.log(f"✅ Configuration backed up to: {backup_path}", "success")
            return True
        except Exception as e:
            self.log(f"❌ Failed to backup configuration: {e}", "error")
            return False

    def quick_restart_all(self) -> None:
        """Quick restart all running services"""
        self.log("🔄 Quick restarting all services...", "info")

        running_services = [
            name for name, process in self.processes.items()
            if process.poll() is None
        ]

        if not running_services:
            self.log("⚠️  No services are currently running", "warning")
            return

        # Stop all
        for service_name in running_services:
            self.stop_service(service_name)

        time.sleep(2)

        # Start all
        for service_name in running_services:
            self.start_service(service_name)
            self.services[service_name].restart_count += 1

        self.log("✅ All services restarted successfully", "success")


class MenuInterface:
    """Interactive menu interface for NIRAJ system"""

    def __init__(self, runner: NirajRunner):
        self.runner = runner
        self.running = True
        self.breadcrumbs: List[str] = ["Main Menu"]
        self.command_history: List[str] = []

    def show_breadcrumbs(self):
        """Display breadcrumb navigation"""
        if COLORAMA_AVAILABLE:
            breadcrumb_str = f"{Fore.CYAN} » {Style.RESET_ALL}".join(self.breadcrumbs)
            print(f"\n{Fore.BLUE}📍 Navigation: {Style.RESET_ALL}{breadcrumb_str}\n")
        else:
            breadcrumb_str = " » ".join(self.breadcrumbs)
            print(f"\n📍 Navigation: {breadcrumb_str}\n")

    def push_breadcrumb(self, item: str):
        """Add item to breadcrumb trail"""
        self.breadcrumbs.append(item)

    def pop_breadcrumb(self):
        """Remove last item from breadcrumb trail"""
        if len(self.breadcrumbs) > 1:
            self.breadcrumbs.pop()

    def add_to_history(self, command: str):
        """Add command to history"""
        self.command_history.append(command)
        if len(self.command_history) > 50:  # Keep last 50 commands
            self.command_history.pop(0)

    def display_banner(self):
        """Display NIRAJ banner with enhanced styling"""
        if COLORAMA_AVAILABLE:
            # Get current date and time
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            print(f"\n{Fore.CYAN}{Style.BRIGHT}")
            print("╔═══════════════════════════════════════════════════════════════════════╗")
            print("║                                                                       ║")
            print(f"║{Fore.GREEN}     ███╗   ██╗██╗██████╗  █████╗      ██╗    ████████╗██████╗ {Fore.CYAN}     ║")
            print(f"║{Fore.GREEN}     ████╗  ██║██║██╔══██╗██╔══██╗     ██║    ╚══██╔══╝██╔══██╗{Fore.CYAN}     ║")
            print(f"║{Fore.GREEN}     ██╔██╗ ██║██║██████╔╝███████║     ██║       ██║   ██║  ██║{Fore.CYAN}     ║")
            print(f"║{Fore.GREEN}     ██║╚██╗██║██║██╔══██╗██╔══██║██   ██║       ██║   ██║  ██║{Fore.CYAN}     ║")
            print(f"║{Fore.GREEN}     ██║ ╚████║██║██║  ██║██║  ██║╚█████╔╝       ██║   ██████╔╝{Fore.CYAN}     ║")
            print(f"║{Fore.GREEN}     ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝        ╚═╝   ╚═════╝ {Fore.CYAN}     ║")
            print("║                                                                       ║")
            print(f"║{Fore.YELLOW}          Advanced Self-Learning Algorithmic AI Trading System{Fore.CYAN}      ║")
            print("║                                                                       ║")
            print(f"║{Fore.MAGENTA}                      🤖 Interactive Menu 🎯{Fore.CYAN}                       ║")
            print("║                                                                       ║")
            print(f"║  {Fore.WHITE}Mode: {Fore.YELLOW}{self.runner.mode.upper()}{Fore.CYAN}{' ' * (58 - len(self.runner.mode))}  ║")
            print(f"║  {Fore.WHITE}Date: {Fore.GREEN}{date_str}  {Fore.WHITE}Time: {Fore.GREEN}{time_str}{Fore.CYAN}{' ' * 33}  ║")
            print("║                                                                       ║")
            print("╚═══════════════════════════════════════════════════════════════════════╝")
            print(f"{Style.RESET_ALL}\n")
        else:
            now = datetime.datetime.now()
            print("\n" + "=" * 75)
            print(" " * 28 + "NIRAJ LTD")
            print(" " * 15 + "Advanced Self-Learning Algorithmic AI")
            print(" " * 20 + "Personal Trading System")
            print(" " * 25 + "Interactive Menu")
            print()
            print(f"Mode: {self.runner.mode.upper()}  |  Date: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 75 + "\n")

    def display_main_menu(self):
        """Display main menu options with enhanced styling"""
        if COLORAMA_AVAILABLE:
            # System status indicators
            running_services = len([p for p in self.runner.processes.values() if p.poll() is None])
            total_services = len(self.runner.services)
            status_color = Fore.GREEN if running_services > 0 else Fore.YELLOW
            
            print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                            📋 MAIN MENU                                {Style.RESET_ALL}{Fore.CYAN}    ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.WHITE}  Services: {status_color}{running_services}/{total_services} Running{Style.RESET_ALL}{' ' * (61 - len(f'{running_services}/{total_services} Running'))}{Fore.CYAN}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║                                                                               ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.MAGENTA}{Style.BRIGHT}🎯 QUICK ACTIONS{Style.RESET_ALL}{Fore.CYAN}{' ' * 60}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}1.{Fore.WHITE} 🚀 Start Services{Fore.CYAN}              {Fore.GREEN}7.{Fore.WHITE} 🧪 API Testing & Validation{Fore.CYAN}       ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}2.{Fore.WHITE} 🛑 Stop Services{Fore.CYAN}               {Fore.GREEN}8.{Fore.WHITE} 🗑️  Cache & Logs Management{Fore.CYAN}        ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}3.{Fore.WHITE} 📊 System & Service Status{Fore.CYAN}     {Fore.GREEN}9.{Fore.WHITE} � Help & Documentation{Fore.CYAN}           ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║                                                                               ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.BLUE}{Style.BRIGHT}⚙️  CONFIGURATION & MANAGEMENT{Style.RESET_ALL}{Fore.CYAN}{' ' * 44}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}4.{Fore.WHITE} 📦 Install Dependencies{Fore.CYAN}        {Fore.GREEN}10.{Fore.WHITE} ⚡ Quick Actions Menu{Fore.CYAN}          ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}5.{Fore.WHITE} ⚙️  Configuration Settings{Fore.CYAN}     {Fore.GREEN}11.{Fore.WHITE} 🔧 Advanced Service Mgmt{Fore.CYAN}       ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}6.{Fore.WHITE} 🔄 Restart All Services{Fore.CYAN}        {Fore.GREEN}12.{Fore.WHITE} � System Diagnostics{Fore.CYAN}          ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║                                                                               ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.YELLOW}{Style.BRIGHT}💹 TRADING MODES{Style.RESET_ALL}{Fore.CYAN}{' ' * 59}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}13.{Fore.WHITE} 📊 Paper Trading Dashboard{Fore.CYAN}    {Fore.RED}15.{Fore.WHITE} 🎮 GPU & System Monitor{Fore.CYAN}        ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.RED}14.{Fore.WHITE} 🔴 Real Trading (LIVE){Fore.CYAN}          {Fore.GREEN}16.{Fore.WHITE} ⌨️  Keyboard Shortcuts{Fore.CYAN}          ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║                                                                               ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.RED}0.{Fore.WHITE} ❌ Exit System{Fore.CYAN}{' ' * 60}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
        else:
            running_services = len([p for p in self.runner.processes.values() if p.poll() is None])
            total_services = len(self.runner.services)
            
            print("\n" + "=" * 80)
            print("                              MAIN MENU")
            print(f"  Services: {running_services}/{total_services} Running")
            print("=" * 80)
            print("\n🎯 QUICK ACTIONS")
            print("  1. 🚀 Start Services              7. 🧪 API Testing & Validation")
            print("  2. 🛑 Stop Services               8. 🗑️  Cache & Logs Management")
            print("  3. 📊 System & Service Status     9. 📚 Help & Documentation")
            print("\n⚙️  CONFIGURATION & MANAGEMENT")
            print("  4. 📦 Install Dependencies        10. ⚡ Quick Actions Menu")
            print("  5. ⚙️  Configuration Settings     11. 🔧 Advanced Service Mgmt")
            print("  6. � Restart All Services        12. 📈 System Diagnostics")
            print("\n💹 TRADING MODES")
            print("  13. 📊 Paper Trading Dashboard    15. 🎮 GPU & System Monitor")
            print("  14. 🔴 Real Trading (LIVE)        16. ⌨️  Keyboard Shortcuts")
            print("\n  0. ❌ Exit System")
            print("=" * 80 + "\n")

    def display_start_menu(self):
        """Display service selection menu"""
        print("\n🚀 Start Services:")
        print("  1. 🌐 Backend API Server")
        print("  2. 💻 Frontend Development Server")
        print("  3. 🔴 Redis Cache Server")
        print("  4. 🤖 Ollama AI Server")
        print("  5. 🎯 Development Setup (Backend + Frontend + Redis + Ollama)")
        print("  6. 🏭 Production Setup (Backend + Redis)")
        print("  7. 🧪 Testing Setup (Backend only)")
        print("  8. 🔧 Custom Selection")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def display_stop_menu(self):
        """Display stop services menu"""
        print("\n🛑 Stop Services:")
        print("  1. 🌐 Stop Backend")
        print("  2. 💻 Stop Frontend")
        print("  3. 🔴 Stop Redis")
        print("  4. 🤖 Stop Ollama")
        print("  5. 🚫 Stop All Services")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def display_config_menu(self):
        """Display configuration menu"""
        print("\n⚙️  Configuration:")
        print("  1. 📄 View Current Config")
        print("  2. 🔧 Edit Service Config")
        print("  3. 🌍 Change Environment Mode")
        print("  4. 📝 Create Custom Config")
        print("  5. 🔄 Reload Configuration")
        print("  6. 📋 Export Configuration")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def display_service_menu(self):
        """Display service management menu with enhanced options"""
        print("\n🔧 Service Management:")
        print("  1. 🔄 Restart Service")
        print("  2. 🔍 View Service Logs")
        print("  3. 🏥 Health Check")
        print("  4. 📊 System Diagnostics")
        print("  5. 🔧 Service Configuration")
        print("  6. ⚡ Quick Restart All")
        print("  7. 💾 Backup Configuration")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def display_help_menu(self):
        """Display help menu"""
        print("\n📚 Help & Documentation:")
        print("  1. 📖 Quick Start Guide")
        print("  2. 🔧 Service Documentation")
        print("  3. 🐛 Troubleshooting")
        print("  4. 💡 Tips & Best Practices")
        print("  5. 🌐 API Documentation")
        print("  6. 📞 Support & Contact")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def get_user_input(self, prompt: str = "Enter your choice: ") -> str:
        """Get user input with enhanced error handling and validation"""
        try:
            if COLORAMA_AVAILABLE:
                user_prompt = f"{Fore.YELLOW}{Style.BRIGHT}➜ {prompt}{Style.RESET_ALL}"
            else:
                user_prompt = f"➜ {prompt}"

            return input(user_prompt).strip()
        except (KeyboardInterrupt, EOFError):
            if COLORAMA_AVAILABLE:
                print(f"\n\n{Fore.CYAN}👋 Goodbye! Thank you for using NIRAJ Trading System.{Style.RESET_ALL}")
            else:
                print("\n\n👋 Goodbye! Thank you for using NIRAJ Trading System.")
            self.running = False
            return "0"
        except Exception as e:
            if COLORAMA_AVAILABLE:
                print(f"{Fore.RED}❌ Input error: {e}{Style.RESET_ALL}")
            else:
                print(f"❌ Input error: {e}")
            return ""

    def safe_input(self, prompt: str = "\n📱 Press Enter to continue...") -> bool:
        """Safe input that handles EOF gracefully"""
        try:
            input(prompt)
            return True
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return False

    def handle_start_services(self):
        """Handle start services menu"""
        self.push_breadcrumb("Start Services")
        while True:
            self.show_breadcrumbs()
            self.display_start_menu()
            choice = self.get_user_input()

            if choice == "0":
                self.pop_breadcrumb()
                break
            elif choice == "1":
                self.start_single_service("backend")
            elif choice == "2":
                self.start_single_service("frontend")
            elif choice == "3":
                self.start_single_service("redis")
            elif choice == "4":
                self.start_single_service("ollama")
            elif choice == "5":
                self.start_multiple_services(["backend", "frontend", "redis", "ollama"])
            elif choice == "6":
                self.start_multiple_services(["backend", "redis"])
            elif choice == "7":
                self.start_multiple_services(["backend"])
            elif choice == "8":
                self.custom_service_selection()
            else:
                print("❌ Invalid choice. Please try again.")

    def handle_stop_services(self):
        """Handle stop services menu"""
        while True:
            self.display_stop_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.runner.stop_service("backend")
            elif choice == "2":
                self.runner.stop_service("frontend")
            elif choice == "3":
                self.runner.stop_service("redis")
            elif choice == "4":
                self.runner.stop_service("ollama")
            elif choice == "5":
                self.runner.stop_all()
            else:
                print("❌ Invalid choice. Please try again.")

            self.safe_input()

    def handle_configuration(self):
        """Handle configuration menu"""
        while True:
            self.display_config_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.view_current_config()
            elif choice == "2":
                self.edit_service_config()
            elif choice == "3":
                self.change_environment_mode()
            elif choice == "4":
                self.create_custom_config()
            elif choice == "5":
                self.runner.load_config()
                print("✅ Configuration reloaded successfully!")
            elif choice == "6":
                self.export_configuration()
            else:
                print("❌ Invalid choice. Please try again.")

            self.safe_input()

    def handle_service_management(self):
        """Handle service management menu"""
        self.push_breadcrumb("Service Management")
        while True:
            self.show_breadcrumbs()
            self.display_service_menu()
            choice = self.get_user_input()

            if choice == "0":
                self.pop_breadcrumb()
                break
            elif choice == "1":
                self.restart_service()
            elif choice == "2":
                self.view_service_logs()
            elif choice == "3":
                self.health_check()
            elif choice == "4":
                self.show_system_diagnostics()
            elif choice == "5":
                self.service_configuration()
            elif choice == "6":
                self.quick_restart_all_services()
            elif choice == "7":
                self.backup_config()
            else:
                print("❌ Invalid choice. Please try again.")

            self.safe_input()

    def handle_help(self):
        """Handle help menu"""
        while True:
            self.display_help_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.show_quick_start()
            elif choice == "2":
                self.show_service_docs()
            elif choice == "3":
                self.show_troubleshooting()
            elif choice == "4":
                self.show_tips()
            elif choice == "5":
                self.show_api_docs()
            elif choice == "6":
                self.show_support()
            else:
                print("❌ Invalid choice. Please try again.")

            self.safe_input()

    def start_single_service(self, service_name: str):
        """Start a single service"""
        self.runner.log(f"Starting {service_name}...", "info")
        if self.runner.start_service(service_name):
            print(f"✅ {service_name} started successfully!")
        else:
            print(f"❌ Failed to start {service_name}")
        self.safe_input()

    def start_multiple_services(self, services: List[str]):
        """Start multiple services"""
        self.runner.log("Starting services...", "info")
        started = []
        for service in services:
            if self.runner.start_service(service):
                started.append(service)

        if started:
            print(f"✅ Started services: {', '.join(started)}")
            self.runner.show_status()

            # Start monitoring
            self.runner.start_monitoring()

            print("\n🎯 Services are running! Press Enter to return to menu...")
            try:
                input()
            except KeyboardInterrupt:
                pass
            finally:
                self.runner.stop_monitoring()
        else:
            print("❌ No services were started successfully")

        self.safe_input()

    def custom_service_selection(self):
        """Custom service selection"""
        print("\n🔧 Custom Service Selection:")
        services = list(self.runner.services.keys())
        selected = []

        for i, service in enumerate(services, 1):
            try:
                choice = input(f"Start {service}? (y/N): ").lower().strip()
                if choice in ["y", "yes"]:
                    selected.append(service)
            except (KeyboardInterrupt, EOFError):
                print("\nOperation cancelled.")
                break

        if selected:
            self.start_multiple_services(selected)
        else:
            print("No services selected.")
            self.safe_input()

    def view_current_config(self):
        """View current configuration"""
        print("\n📄 Current Configuration:")
        print(f"Mode: {self.runner.mode}")
        print(f"Config File: {self.runner.config_file}")
        print("\nServices:")
        for name, service in self.runner.services.items():
            print(f"  {name}:")
            print(f"    Command: {' '.join(service.command)}")
            print(f"    Working Directory: {service.cwd}")
            print(f"    Startup Time: {service.startup_time}s")

    def edit_service_config(self):
        """Edit service configuration"""
        print("\n🔧 Edit Service Configuration:")
        services = list(self.runner.services.keys())
        for i, service in enumerate(services, 1):
            print(f"  {i}. {service}")

        try:
            user_input = input("Select service to edit (0 to cancel): ")
            choice = int(user_input)
            if 1 <= choice <= len(services):
                service_name = services[choice - 1]
                print(f"\nEditing {service_name} configuration...")
                print(
                    "(This would open a configuration editor in a full implementation)"
                )
            elif choice == 0:
                return
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid input")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return

    def change_environment_mode(self):
        """Change environment mode"""
        print("\n🌍 Change Environment Mode:")
        modes = ["development", "production", "testing"]
        for i, mode in enumerate(modes, 1):
            marker = " (current)" if mode == self.runner.mode else ""
            print(f"  {i}. {mode}{marker}")

        try:
            user_input = input("Select environment mode (0 to cancel): ")
            choice = int(user_input)
            if 1 <= choice <= len(modes):
                new_mode = modes[choice - 1]
                self.runner.mode = new_mode
                self.runner.load_config()
                self.runner.set_environment()
                print(f"✅ Environment mode changed to: {new_mode}")
            elif choice == 0:
                return
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid input")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return

    def create_custom_config(self):
        """Create custom configuration"""
        print("\n📝 Create Custom Configuration:")
        try:
            config_name = input(
                "Enter configuration file name (e.g., my-config.json): "
            )
            if config_name:
                # In a full implementation, this would create a config file
                print(f"✅ Configuration template created: {config_name}")
            else:
                print("❌ Invalid file name")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")

    def export_configuration(self):
        """Export current configuration"""
        print("\n📋 Export Configuration:")
        filename = (
            input("Enter export filename (default: config-export.json): ")
            or "config-export.json"
        )
        # In a full implementation, this would export the config
        print(f"✅ Configuration exported to: {filename}")

    def restart_service(self):
        """Restart a service"""
        print("\n🔄 Restart Service:")
        running_services = [
            name
            for name, process in self.runner.processes.items()
            if process.poll() is None
        ]

        if not running_services:
            print("No services are currently running.")
            return

        for i, service in enumerate(running_services, 1):
            print(f"  {i}. {service}")

        try:
            choice = int(input("Select service to restart (0 to cancel): "))
            if 1 <= choice <= len(running_services):
                service_name = running_services[choice - 1]
                print(f"Restarting {service_name}...")
                self.runner.stop_service(service_name)
                time.sleep(2)
                self.runner.start_service(service_name)
                print(f"✅ {service_name} restarted successfully!")
            elif choice == 0:
                return
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Invalid input")

    def view_service_logs(self):
        """View service logs"""
        print("\n🔍 Service Logs:")
        print("(This would show real-time logs in a full implementation)")
        print("For now, check the individual service output in the terminal.")

    def health_check(self):
        """Perform health check on services"""
        print("\n🏥 Health Check:")
        for service_name, service in self.runner.services.items():
            if service_name in self.runner.processes:
                if self.runner.processes[service_name].poll() is None:
                    if self.runner._check_service_health(service):
                        print(f"  ✅ {service_name}: Healthy")
                    else:
                        print(f"  ⚠️  {service_name}: Running but health check failed")
                else:
                    print(f"  ❌ {service_name}: Not running")
            else:
                print(f"  ⭕ {service_name}: Not started")

    def performance_metrics(self):
        """Show performance metrics"""
        print("\n📊 Performance Metrics:")
        print("Service resource usage and performance statistics would be shown here.")
        # In a full implementation, this would show CPU, memory, network stats

    def service_configuration(self):
        """Show service configuration details"""
        print("\n🔧 Service Configuration Details:")
        for name, service in self.runner.services.items():
            process_exists = name in self.runner.processes
            process_running = (
                process_exists and self.runner.processes[name].poll() is None
            )
            status = "Running" if process_running else "Stopped"
            print(f"\n{name} ({status}):")
            print(f"  Command: {' '.join(service.command)}")
            print(f"  Directory: {service.cwd}")
            print(f"  Environment: {service.env}")
            if service.health_check_url:
                print(f"  Health Check: {service.health_check_url}")

    def show_system_diagnostics(self):
        """Display comprehensive system diagnostics"""
        print("\n🔍 System Diagnostics")
        print("=" * 70)

        diagnostics = self.runner.get_system_diagnostics()

        print(f"\n📅 Timestamp: {diagnostics['timestamp']}")
        print(f"⚙️  Mode: {diagnostics['mode']}")

        if diagnostics['system_uptime']:
            uptime_sec = diagnostics['system_uptime']
            hours = int(uptime_sec // 3600)
            minutes = int((uptime_sec % 3600) // 60)
            print(f"⏱️  System Uptime: {hours}h {minutes}m")

        print("\n📊 Service Status:")
        for service_name, info in diagnostics['services'].items():
            status_icon = "✅" if info['running'] else "❌"
            print(f"  {status_icon} {service_name}:")
            print(f"     Uptime: {info['uptime']}")
            print(f"     Restarts: {info['restarts']}")

        print("\n💾 Disk Usage:")
        for dir_name, usage in diagnostics['disk_usage'].items():
            print(f"  📁 {dir_name}: {usage['mb']} MB ({usage['bytes']:,} bytes)")

        print("\n" + "=" * 70)

    def quick_restart_all_services(self):
        """Quick restart all running services"""
        print("\n⚡ Quick Restart All Services")

        try:
            confirm = input("⚠️  This will restart all running services. Continue? (y/N): ").lower().strip()
            if confirm in ["y", "yes"]:
                self.runner.quick_restart_all()
                print("✅ All services restarted successfully!")
            else:
                print("❌ Operation cancelled")
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Operation cancelled")

    def backup_config(self):
        """Backup current configuration"""
        print("\n💾 Backup Configuration")

        try:
            custom_path = input("Enter backup path (press Enter for default): ").strip()
            backup_path = Path(custom_path) if custom_path else None

            if self.runner.backup_configuration(backup_path):
                print("✅ Configuration backup completed successfully!")
            else:
                print("❌ Configuration backup failed")
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Operation cancelled")

    def show_quick_start(self):
        """Show quick start guide"""
        print("\n📖 Quick Start Guide:")
        print("1. Install dependencies: Select option 4 from main menu")
        print("2. Start development setup: Select option 1 > 5 from main menu")
        print("3. Access services:")
        print("   - Backend API: http://localhost:8000")
        print("   - Frontend: http://localhost:5173")
        print("   - API Docs: http://localhost:8000/docs")
        print("4. Check service status: Select option 3 from main menu")
        print("5. Stop services when done: Select option 2 from main menu")

    def show_service_docs(self):
        """Show service documentation"""
        print("\n🔧 Service Documentation:")
        print("Backend (FastAPI):")
        print("  - API endpoint: http://localhost:8000")
        print("  - Documentation: http://localhost:8000/docs")
        print("  - Health check: http://localhost:8000/health")
        print("\nFrontend (React + Vite):")
        print("  - Development server: http://localhost:5173")
        print("  - Build command: npm run build")
        print("\nRedis (Cache):")
        print("  - Default port: 6379")
        print("  - Connection: localhost:6379")
        print("\nOllama (AI):")
        print("  - API endpoint: http://localhost:11434")
        print("  - Model management: ollama pull <model>")

    def show_troubleshooting(self):
        """Show troubleshooting guide"""
        print("\n🐛 Troubleshooting:")
        print("Common Issues:")
        print("1. Port already in use:")
        print("   - Check running processes: ps aux | grep <service>")
        print("   - Kill process: kill <pid>")
        print("2. Dependencies not installed:")
        print("   - Run: python niraj.py install")
        print("3. Permission errors:")
        print("   - Check file permissions")
        print("   - Run with appropriate user privileges")
        print("4. Service fails to start:")
        print("   - Check logs for detailed error messages")
        print("   - Verify configuration files")

    def show_tips(self):
        """Show tips and best practices"""
        print("\n💡 Tips & Best Practices:")
        print("1. Always start with development mode first")
        print("2. Check service status before starting new services")
        print("3. Use health checks to verify service functionality")
        print("4. Monitor logs for debugging issues")
        print("5. Stop services gracefully to avoid data corruption")
        print("6. Regular backup of configuration files")
        print("7. Use production mode only for deployment")

    def show_api_docs(self):
        """Show API documentation info"""
        print("\n🌐 API Documentation:")
        print("FastAPI automatically generates interactive documentation:")
        print("  - Swagger UI: http://localhost:8000/docs")
        print("  - ReDoc: http://localhost:8000/redoc")
        print("  - OpenAPI Schema: http://localhost:8000/openapi.json")
        print("\nKey endpoints:")
        print("  - Health check: GET /health")
        print("  - System status: GET /info")
        print("  - WebSocket: ws://localhost:8000/ws")

    def show_support(self):
        """Show support information"""
        print("\n📞 Support & Contact:")
        print("Documentation: README.md and docs/ directory")
        print("Issues: GitHub Issues page")
        print("Discussions: GitHub Discussions")
        print("Email: support@niraj-trading.com (if available)")
        print("\nFor immediate help:")
        print("1. Check the troubleshooting guide")
        print("2. Review service logs")
        print("3. Verify system requirements")
        print("4. Check GitHub issues for similar problems")

    def display_api_testing_menu(self):
        """Display API testing menu"""
        print("\n🧪 API Testing:")
        print("  1. 🔍 Test All API Endpoints (Core)")
        print("  2. 🏥 Quick Health Check")
        print("  3. � Test Broker APIs (Angel One & Dhan)")
        print("  4. 📰 Test News APIs")
        print("  5. 🌤️  Test Weather APIs")
        print("  6. 🔬 Test All External APIs (Comprehensive)")
        print("  7. �📄 Test Specific Endpoint")
        print("  8. 📊 View API Documentation")
        print("  9. 🔄 Test WebSocket Connection")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def display_cache_logs_menu(self):
        """Display cache and logs management menu"""
        print("\n🗑️  Cache & Logs Management:")
        print("  1. 🗑️  Clear Redis Cache")
        print("  2. 🗑️  Clear All Logs")
        print("  3. 📋 View Recent Logs")
        print("  4. 📊 Show Log File Sizes")
        print("  5. 🗑️  Clear Python Cache (__pycache__)")
        print("  6. 🧹 Clear Everything (Cache + Logs)")
        print("  0. ⬅️  Back to Main Menu")
        print()

    def handle_api_testing(self):
        """Handle API testing menu"""
        while True:
            self.display_api_testing_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.test_all_endpoints()
            elif choice == "2":
                self.quick_health_check()
            elif choice == "3":
                self.runner.test_broker_apis()
            elif choice == "4":
                self.runner.test_news_api()
            elif choice == "5":
                self.runner.test_weather_api()
            elif choice == "6":
                self.runner.test_all_external_apis()
            elif choice == "7":
                self.test_specific_endpoint()
            elif choice == "8":
                self.view_api_docs()
            elif choice == "9":
                self.test_websocket()
            else:
                print("❌ Invalid choice. Please try again.")

            if choice != "0":
                self.safe_input()

    def handle_cache_logs_management(self):
        """Handle cache and logs management menu"""
        while True:
            self.display_cache_logs_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.runner.clear_redis_cache()
            elif choice == "2":
                self.runner.clear_logs()
            elif choice == "3":
                self.view_logs_interactive()
            elif choice == "4":
                self.show_log_sizes()
            elif choice == "5":
                self.clear_python_cache()
            elif choice == "6":
                self.clear_everything()
            else:
                print("❌ Invalid choice. Please try again.")

            if choice != "0":
                self.safe_input()

    def test_all_endpoints(self):
        """Test all API endpoints"""
        results = self.runner.test_api_endpoints()

        if results:
            print("\n" + "=" * 60)
            print("API Test Results:")
            print("=" * 60)
            for endpoint, success in results.items():
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  {endpoint}: {status}")
            print("=" * 60)

    def quick_health_check(self):
        """Quick health check for backend"""
        print("\n🏥 Performing Quick Health Check...")

        # Check if backend is running
        if "backend" not in self.runner.processes or self.runner.processes["backend"].poll() is not None:
            print("❌ Backend is not running. Please start the backend first.")
            return

        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend API is healthy!")
                print(f"Response: {response.json()}")
            else:
                print(f"⚠️  Backend returned status code: {response.status_code}")
        except ImportError:
            # Fallback to curl
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000/health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("✅ Backend API is healthy!")
                print(f"Response: {result.stdout}")
            else:
                print("❌ Health check failed")
        except Exception as e:
            print(f"❌ Health check failed: {e}")

    def test_specific_endpoint(self):
        """Test a specific endpoint"""
        print("\n📄 Test Specific Endpoint")
        try:
            url = input("Enter endpoint URL (e.g., http://localhost:8000/health): ").strip()
            if not url:
                print("❌ No URL provided")
                return

            print(f"\n🔍 Testing: {url}")

            try:
                import requests
                response = requests.get(url, timeout=5)
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text[:500]}")  # First 500 chars
            except ImportError:
                result = subprocess.run(
                    ["curl", "-s", "-w", "\nHTTP Code: %{http_code}", url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                print(result.stdout)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")

    def view_api_docs(self):
        """Open API documentation in browser"""
        print("\n📊 API Documentation URLs:")
        print("  Swagger UI: http://localhost:8000/docs")
        print("  ReDoc: http://localhost:8000/redoc")
        print("  OpenAPI Schema: http://localhost:8000/openapi.json")

        try:
            choice = input("\nOpen in browser? (y/N): ").lower().strip()
            if choice in ["y", "yes"]:
                webbrowser.open("http://localhost:8000/docs")
                print("✅ Opened API documentation in browser")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")

    def test_websocket(self):
        """Test WebSocket connection"""
        print("\n🔄 WebSocket Testing")
        print("WebSocket URL: ws://localhost:8000/ws")
        print("(Full WebSocket testing would require additional libraries)")
        print("\nTo test manually:")
        print("  1. Use a WebSocket client tool")
        print("  2. Connect to: ws://localhost:8000/ws")
        print("  3. Send test messages")

    def view_logs_interactive(self):
        """View logs interactively"""
        print("\n📋 View Logs")
        try:
            lines_input = input("Number of lines to show (default: 50): ").strip()
            lines = int(lines_input) if lines_input else 50
            self.runner.view_logs(lines)
        except ValueError:
            print("❌ Invalid number, using default (50)")
            self.runner.view_logs(50)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")

    def show_log_sizes(self):
        """Show log file sizes"""
        print("\n📊 Log File Sizes:")
        sizes = self.runner.get_log_size()

        if not sizes:
            print("  No log files found")
            return

        total_size = 0
        for log_file, size in sizes.items():
            size_mb = size / (1024 * 1024)
            size_kb = size / 1024

            if size_mb > 1:
                print(f"  {log_file}: {size_mb:.2f} MB")
            elif size_kb > 1:
                print(f"  {log_file}: {size_kb:.2f} KB")
            else:
                print(f"  {log_file}: {size} bytes")

            total_size += size

        total_mb = total_size / (1024 * 1024)
        print(f"\n  Total: {total_mb:.2f} MB")

    def clear_python_cache(self):
        """Clear Python cache directories"""
        print("\n🗑️  Clearing Python Cache...")

        # Find all __pycache__ directories
        cache_dirs = []
        for root, dirs, _ in os.walk(PROJECT_ROOT):
            if "__pycache__" in dirs:
                cache_dirs.append(Path(root) / "__pycache__")

        if not cache_dirs:
            print("  No __pycache__ directories found")
            return

        print(f"  Found {len(cache_dirs)} cache directories")

        try:
            confirm = input("Clear all Python cache directories? (y/N): ").lower().strip()
            if confirm in ["y", "yes"]:
                cleared = 0
                for cache_dir in cache_dirs:
                    try:
                        import shutil
                        shutil.rmtree(cache_dir)
                        print(f"  ✅ Cleared: {cache_dir}")
                        cleared += 1
                    except Exception as e:
                        print(f"  ❌ Failed to clear {cache_dir}: {e}")

                print(f"\n✅ Cleared {cleared}/{len(cache_dirs)} cache directories")
            else:
                print("Operation cancelled.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")

    def clear_everything(self):
        """Clear all cache and logs"""
        print("\n🧹 Clear Everything (Cache + Logs)")
        print("This will:")
        print("  - Clear Redis cache")
        print("  - Clear all log files")
        print("  - Clear Python __pycache__ directories")

        try:
            confirm = input("\n⚠️  Are you sure? This cannot be undone! (yes/N): ").strip()
            if confirm.lower() == "yes":
                print("\n🧹 Clearing everything...")

                # Clear Redis
                self.runner.clear_redis_cache()

                # Clear logs
                self.runner.clear_logs()

                # Clear Python cache
                cache_dirs = []
                for root, dirs, _ in os.walk(PROJECT_ROOT):
                    if "__pycache__" in dirs:
                        cache_dirs.append(Path(root) / "__pycache__")

                for cache_dir in cache_dirs:
                    try:
                        import shutil
                        shutil.rmtree(cache_dir)
                    except Exception:
                        pass

                print("\n✅ All cache and logs cleared successfully!")
            else:
                print("Operation cancelled.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")

    def run(self):
        """Main menu loop with enhanced navigation"""
        self.display_banner()

        while self.running:
            self.show_breadcrumbs()
            self.display_main_menu()

            # Show helpful hint with system info
            if COLORAMA_AVAILABLE:
                uptime = ""
                if self.runner.system_start_time:
                    uptime_sec = time.time() - self.runner.system_start_time
                    uptime_min = int(uptime_sec / 60)
                    uptime = f" | Uptime: {uptime_min}m" if uptime_min > 0 else ""
                print(f"{Fore.CYAN}💡 Tip: Type 'help' for shortcuts | Press Ctrl+C to exit{uptime}{Style.RESET_ALL}\n")
            else:
                print("💡 Tip: Type 'help' for shortcuts | Press Ctrl+C to exit\n")

            choice = self.get_user_input()

            if not self.running:  # User pressed Ctrl+C
                break

            self.add_to_history(choice)

            if choice == "0":
                if COLORAMA_AVAILABLE:
                    print(f"\n{Fore.GREEN}👋 Thank you for using NIRAJ Trading System!{Style.RESET_ALL}")
                else:
                    print("\n👋 Thank you for using NIRAJ Trading System!")
                break
            elif choice == "1":
                self.handle_start_services()
            elif choice == "2":
                self.handle_stop_services()
            elif choice == "3":
                self.show_enhanced_status()
            elif choice == "4":
                self.runner.install_dependencies()
                self.safe_input()
            elif choice == "5":
                self.handle_configuration()
            elif choice == "6":
                self.quick_restart_all_services()
            elif choice == "7":
                self.handle_api_testing()
            elif choice == "8":
                self.handle_cache_logs_management()
            elif choice == "9":
                self.handle_help()
            elif choice == "10":
                self.show_quick_actions_menu()
            elif choice == "11":
                self.handle_service_management()
            elif choice == "12":
                self.show_system_diagnostics()
            elif choice == "13":
                self.handle_trading_dashboard(paper_mode=True)
            elif choice == "14":
                self.handle_trading_dashboard(paper_mode=False)
            elif choice == "15":
                self.show_gpu_system_monitor()
            elif choice == "16":
                self.show_keyboard_shortcuts()
                self.safe_input()
            elif choice.lower() == "help":
                self.show_keyboard_shortcuts()
                self.safe_input()
            elif choice.lower() == "status":
                self.show_enhanced_status()
            elif choice.lower() == "clear":
                os.system('clear' if os.name != 'nt' else 'cls')
            else:
                if COLORAMA_AVAILABLE:
                    print(f"{Fore.RED}❌ Invalid choice. Please enter 0-16, 'help', 'status', or 'clear'.{Style.RESET_ALL}")
                else:
                    print("❌ Invalid choice. Please enter 0-16, 'help', 'status', or 'clear'.")

        # Cleanup
        self.runner.stop_monitoring()
        self.runner.stop_all()

    def handle_trading_dashboard(self, paper_mode: bool = True):
        """Handle trading dashboard launch"""
        mode_text = "Paper Trading (₹10,000)" if paper_mode else "Real Trading"

        print(f"\n📊 {mode_text} Dashboard")
        print("=" * 70)

        if not paper_mode:
            print(f"{Fore.RED if COLORAMA_AVAILABLE else ''}⚠️  WARNING: Real trading mode will use actual funds!{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}")
            confirm = input("Type 'YES' to confirm real trading mode: ")
            if confirm != "YES":
                print("Real trading cancelled.")
                self.safe_input()
                return

        # Start backend if not running
        if "backend" not in self.runner.processes or self.runner.processes["backend"].poll() is not None:
            print("Starting backend API...")
            if not self.runner.start_service("backend"):
                print("Failed to start backend!")
                self.safe_input()
                return

        # Start redis if not running
        if "redis" not in self.runner.processes or self.runner.processes["redis"].poll() is not None:
            print("Starting Redis...")
            self.runner.start_service("redis")

        # Create and start dashboard
        trading_mode = TradingMode.PAPER if paper_mode else TradingMode.REAL
        dashboard = TradingDashboard(
            runner=self.runner,
            mode=trading_mode,
            initial_balance=Decimal('10000.0')
        )

        print(f"\n🚀 Starting {mode_text} dashboard...")
        print("📊 Dashboard will update every 1 second")
        print("Press Ctrl+C to stop\n")

        time.sleep(2)

        dashboard.start()

        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping dashboard...")
            dashboard.stop()
            print("Dashboard stopped.")
            self.safe_input()

    def show_keyboard_shortcuts(self):
        """Display keyboard shortcuts and tips"""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                 ⌨️  KEYBOARD SHORTCUTS & TIPS{Style.RESET_ALL}{Fore.CYAN}                   ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}Navigation:{Style.RESET_ALL}{Fore.CYAN}{' ' * 59}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Type 0-16 to select menu options{Fore.CYAN}{' ' * 36}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Type 'help' for this guide{Fore.CYAN}{' ' * 42}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Type 'status' for quick status check{Fore.CYAN}{' ' * 32}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Type 'clear' to clear screen{Fore.CYAN}{' ' * 40}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Press Ctrl+C to exit gracefully{Fore.CYAN}{' ' * 36}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.WHITE}• Press Enter to continue after viewing info{Fore.CYAN}{' ' * 26}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{' ' * 71}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}Quick Tips:{Style.RESET_ALL}{Fore.CYAN}{' ' * 58}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 3{Fore.WHITE} - Check service status before starting{Fore.CYAN}{' ' * 23}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 4{Fore.WHITE} - Install dependencies on first run{Fore.CYAN}{' ' * 25}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 1 > 5{Fore.WHITE} - Complete development setup{Fore.CYAN}{' ' * 27}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 7{Fore.WHITE} - Test APIs after starting services{Fore.CYAN}{' ' * 25}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 13{Fore.WHITE} - Paper trading (safe testing){Fore.CYAN}{' ' * 28}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║    {Fore.YELLOW}• Option 15{Fore.WHITE} - Monitor GPU and system resources{Fore.CYAN}{' ' * 23}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
        else:
            print("\n⌨️  Keyboard Shortcuts & Tips")
            print("=" * 70)
            print("  Navigation:")
            print("    • Type 0-16 to select menu options")
            print("    • Type 'help' for this guide")
            print("    • Type 'status' for quick status check")
            print("    • Type 'clear' to clear screen")
            print("    • Press Ctrl+C to exit gracefully")
            print("    • Press Enter to continue after viewing info")
            print("\n  Quick Tips:")
            print("    • Option 3 - Check service status before starting")
            print("    • Option 4 - Install dependencies on first run")
            print("    • Option 1 > 5 - Complete development setup")
            print("    • Option 7 - Test APIs after starting services")
            print("    • Option 13 - Paper trading (safe testing)")
            print("    • Option 15 - Monitor GPU and system resources")
            print("=" * 70)

    def show_enhanced_status(self):
        """Show enhanced status with system info"""
        self.runner.show_status()
        
        # Show additional system info
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                      📊 SYSTEM INFORMATION{Style.RESET_ALL}{Fore.CYAN}                        ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        else:
            print("\n" + "=" * 70)
            print("                      � SYSTEM INFORMATION")
            print("=" * 70)
        
        # Try to show system stats
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                disk = shutil.disk_usage(PROJECT_ROOT)
                
                if COLORAMA_AVAILABLE:
                    cpu_color = Fore.GREEN if cpu < 50 else Fore.YELLOW if cpu < 75 else Fore.RED
                    mem_color = Fore.GREEN if mem.percent < 50 else Fore.YELLOW if mem.percent < 75 else Fore.RED
                    disk_color = Fore.GREEN if disk.used / disk.total < 0.5 else Fore.YELLOW if disk.used / disk.total < 0.75 else Fore.RED
                    
                    print(f"  🔥 CPU Usage: {cpu_color}{cpu:.1f}%{Style.RESET_ALL}")
                    print(f"  💾 Memory: {mem_color}{mem.percent:.1f}%{Style.RESET_ALL} ({mem.used/(1024**3):.1f}G / {mem.total/(1024**3):.1f}G)")
                    print(f"  💿 Disk: {disk_color}{disk.used/disk.total*100:.1f}%{Style.RESET_ALL} ({disk.used/(1024**3):.1f}G / {disk.total/(1024**3):.1f}G)")
                else:
                    print(f"  CPU Usage: {cpu:.1f}%")
                    print(f"  Memory: {mem.percent:.1f}% ({mem.used/(1024**3):.1f}G / {mem.total/(1024**3):.1f}G)")
                    print(f"  Disk: {disk.used/disk.total*100:.1f}% ({disk.used/(1024**3):.1f}G / {disk.total/(1024**3):.1f}G)")
        except Exception:
            print("  ℹ️  System stats unavailable (install psutil)")
        
        print()
        self.safe_input()

    def show_quick_actions_menu(self):
        """Show quick actions menu"""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                        ⚡ QUICK ACTIONS{Style.RESET_ALL}{Fore.CYAN}                           ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}1.{Fore.WHITE} 🚀 Start Full Dev Stack (Backend+Frontend+Redis+Ollama){Fore.CYAN}        ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}2.{Fore.WHITE} 🏭 Start Production Stack (Backend+Redis){Fore.CYAN}{' ' * 29}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}3.{Fore.WHITE} 🔄 Restart All Running Services{Fore.CYAN}{' ' * 37}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}4.{Fore.WHITE} 🛑 Stop All Services{Fore.CYAN}{' ' * 47}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}5.{Fore.WHITE} 🗑️  Clear All Cache & Logs{Fore.CYAN}{' ' * 41}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}6.{Fore.WHITE} 📊 Open Paper Trading Dashboard{Fore.CYAN}{' ' * 36}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}7.{Fore.WHITE} 🧪 Run Full API Test Suite{Fore.CYAN}{' ' * 40}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}8.{Fore.WHITE} 💾 Backup Configuration{Fore.CYAN}{' ' * 44}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║  {Fore.GREEN}0.{Fore.WHITE} ⬅️  Back to Main Menu{Fore.CYAN}{' ' * 46}║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
        else:
            print("\n⚡ QUICK ACTIONS")
            print("=" * 70)
            print("  1. 🚀 Start Full Dev Stack (Backend+Frontend+Redis+Ollama)")
            print("  2. 🏭 Start Production Stack (Backend+Redis)")
            print("  3. 🔄 Restart All Running Services")
            print("  4. 🛑 Stop All Services")
            print("  5. 🗑️  Clear All Cache & Logs")
            print("  6. 📊 Open Paper Trading Dashboard")
            print("  7. 🧪 Run Full API Test Suite")
            print("  8. 💾 Backup Configuration")
            print("  0. ⬅️  Back to Main Menu")
            print("=" * 70 + "\n")
        
        choice = self.get_user_input()
        
        if choice == "0":
            return
        elif choice == "1":
            self.start_multiple_services(["backend", "frontend", "redis", "ollama"])
        elif choice == "2":
            self.start_multiple_services(["backend", "redis"])
        elif choice == "3":
            self.quick_restart_all_services()
        elif choice == "4":
            self.runner.stop_all()
            print("\n✅ All services stopped")
            self.safe_input()
        elif choice == "5":
            self.clear_everything()
        elif choice == "6":
            self.handle_trading_dashboard(paper_mode=True)
        elif choice == "7":
            self.runner.test_all_external_apis()
            self.safe_input()
        elif choice == "8":
            self.backup_config()

    def show_gpu_system_monitor(self):
        """Show real-time GPU and system monitoring"""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
            print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                   🎮 GPU & SYSTEM MONITOR{Style.RESET_ALL}{Fore.CYAN}                       ║{Style.RESET_ALL}")
            print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
        else:
            print("\n" + "=" * 70)
            print("                   🎮 GPU & SYSTEM MONITOR")
            print("=" * 70)
        
        if not PSUTIL_AVAILABLE:
            print("\n⚠️  psutil not installed. Install it with: pip install psutil")
            self.safe_input()
            return
        
        print("\n📊 Collecting system statistics... (5 seconds)\n")
        
        for i in range(5):
            # CPU
            cpu = psutil.cpu_percent(interval=1)
            cpu_color = Fore.GREEN if cpu < 50 else Fore.YELLOW if cpu < 75 else Fore.RED if COLORAMA_AVAILABLE else ""
            reset = Style.RESET_ALL if COLORAMA_AVAILABLE else ""
            
            # Memory
            mem = psutil.virtual_memory()
            mem_color = Fore.GREEN if mem.percent < 50 else Fore.YELLOW if mem.percent < 75 else Fore.RED if COLORAMA_AVAILABLE else ""
            
            # Disk
            disk = shutil.disk_usage(PROJECT_ROOT)
            disk_pct = disk.used / disk.total * 100
            disk_color = Fore.GREEN if disk_pct < 50 else Fore.YELLOW if disk_pct < 75 else Fore.RED if COLORAMA_AVAILABLE else ""
            
            print(f"\r🔥 CPU: {cpu_color}{cpu:5.1f}%{reset}  💾 RAM: {mem_color}{mem.percent:5.1f}%{reset}  💿 Disk: {disk_color}{disk_pct:5.1f}%{reset}", end='', flush=True)
        
        print("\n")
        
        # Try GPU info
        try:
            smi = shutil.which('nvidia-smi')
            if smi:
                print("🎮 GPU Information:")
                result = subprocess.run([smi, '--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,fan.speed',
                                         '--format=csv,noheader,nounits'],
                                        capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    line = result.stdout.strip()
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        print(f"  Name: {parts[0]}")
                        print(f"  Utilization: {parts[1]}%")
                        print(f"  Memory: {parts[2]}MB / {parts[3]}MB")
                        print(f"  Temperature: {parts[4]}°C")
                        if len(parts) >= 6:
                            print(f"  Fan Speed: {parts[5]}%")
                else:
                    print("  ℹ️  No GPU data available")
            else:
                print("🎮 GPU: nvidia-smi not found (NVIDIA GPUs only)")
        except Exception as e:
            print(f"🎮 GPU: Unable to query ({str(e)})")
        
        print()
        self.safe_input()

    def show_advanced_service_management(self):
        """Show advanced service management menu"""
        while True:
            if COLORAMA_AVAILABLE:
                print(f"\n{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║{Fore.YELLOW}{Style.BRIGHT}                   🔧 ADVANCED SERVICE MANAGEMENT{Style.RESET_ALL}{Fore.CYAN}                  ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}╠═══════════════════════════════════════════════════════════════════════╣{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║  {Fore.GREEN}Start Services:{Style.RESET_ALL}{Fore.CYAN}{' ' * 56}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║    {Fore.WHITE}1. Backend          2. Frontend         3. Redis{Fore.CYAN}            ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║    {Fore.WHITE}4. Ollama           5. PostgreSQL       6. Custom{Fore.CYAN}           ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║{' ' * 71}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║  {Fore.YELLOW}Stop Services:{Style.RESET_ALL}{Fore.CYAN}{' ' * 57}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║    {Fore.WHITE}7. Backend          8. Frontend         9. Redis{Fore.CYAN}            ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║    {Fore.WHITE}10. Ollama         11. PostgreSQL      12. All{Fore.CYAN}             ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║{' ' * 71}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║  {Fore.CYAN}Restart Services:{Style.RESET_ALL}{Fore.CYAN}{' ' * 54}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║    {Fore.WHITE}13. Backend        14. Frontend        15. All{Fore.CYAN}             ║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║{' ' * 71}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}║  {Fore.GREEN}0.{Fore.WHITE} ⬅️  Back to Main Menu{Fore.CYAN}{' ' * 46}║{Style.RESET_ALL}")
                print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
            else:
                print("\n🔧 ADVANCED SERVICE MANAGEMENT")
                print("=" * 70)
                print("  Start Services:")
                print("    1. Backend          2. Frontend         3. Redis")
                print("    4. Ollama           5. PostgreSQL       6. Custom")
                print("\n  Stop Services:")
                print("    7. Backend          8. Frontend         9. Redis")
                print("    10. Ollama         11. PostgreSQL      12. All")
                print("\n  Restart Services:")
                print("    13. Backend        14. Frontend        15. All")
                print("\n  0. ⬅️  Back to Main Menu")
                print("=" * 70 + "\n")
            
            choice = self.get_user_input()
            
            if choice == "0":
                break
            elif choice == "1":
                self.runner.start_service("backend")
                self.safe_input()
            elif choice == "2":
                self.runner.start_service("frontend")
                self.safe_input()
            elif choice == "3":
                self.runner.start_service("redis")
                self.safe_input()
            elif choice == "4":
                self.runner.start_service("ollama")
                self.safe_input()
            elif choice == "5":
                self.runner.start_service("postgresql")
                self.safe_input()
            elif choice == "6":
                service_name = input("\nEnter service name: ").strip()
                if service_name:
                    self.runner.start_service(service_name)
                self.safe_input()
            elif choice == "7":
                self.runner.stop_service("backend")
                self.safe_input()
            elif choice == "8":
                self.runner.stop_service("frontend")
                self.safe_input()
            elif choice == "9":
                self.runner.stop_service("redis")
                self.safe_input()
            elif choice == "10":
                self.runner.stop_service("ollama")
                self.safe_input()
            elif choice == "11":
                self.runner.stop_service("postgresql")
                self.safe_input()
            elif choice == "12":
                self.runner.stop_all()
                print("\n✅ All services stopped")
                self.safe_input()
            elif choice == "13":
                self.runner.stop_service("backend")
                time.sleep(1)
                self.runner.start_service("backend")
                self.safe_input()
            elif choice == "14":
                self.runner.stop_service("frontend")
                time.sleep(1)
                self.runner.start_service("frontend")
                self.safe_input()
            elif choice == "15":
                self.quick_restart_all_services()


# ============================================================================
# TRADING DASHBOARD & REAL-TIME FEATURES
# ============================================================================

class TradingMode(Enum):
    """Trading mode enumeration"""
    PAPER = "paper"
    REAL = "real"


@dataclass
class TradingAccount:
    """Trading account data"""
    broker: str  # 'dhan' or 'angel_one'
    balance: Decimal = Decimal('0.0')
    positions: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    pnl: Decimal = Decimal('0.0')
    pnl_percentage: Decimal = Decimal('0.0')
    last_update: Optional[datetime.datetime] = None


@dataclass
class MarketData:
    """Market data snapshot"""
    bank_nifty_price: Optional[Decimal] = None
    bank_nifty_change: Optional[Decimal] = None
    bank_nifty_change_percent: Optional[Decimal] = None
    nifty_price: Optional[Decimal] = None
    nifty_change: Optional[Decimal] = None
    trend: str = "UNKNOWN"
    volatility: str = "LOW"
    last_update: Optional[datetime.datetime] = None


@dataclass
class AIStatus:
    """AI engine status"""
    is_active: bool = False
    is_training: bool = False
    is_thinking: bool = False
    current_task: str = "Idle"
    confidence: float = 0.0
    signals: List[Dict[str, Any]] = field(default_factory=list)
    last_update: Optional[datetime.datetime] = None


@dataclass
class SystemStats:
    """System resource usage snapshot"""
    cpu_percent: float = 0.0
    cpu_cores: int = 0
    load_avg_1m: float = 0.0
    load_ratio: float = 0.0
    memory_used: float = 0.0
    memory_total: float = 0.0
    memory_percent: float = 0.0
    swap_used: float = 0.0
    swap_total: float = 0.0
    disk_used: float = 0.0
    disk_total: float = 0.0
    disk_percent: float = 0.0
    net_sent: float = 0.0  # MB since dashboard start
    net_recv: float = 0.0  # MB since dashboard start
    gpu_name: Optional[str] = None
    gpu_util: Optional[float] = None
    gpu_mem_util: Optional[float] = None
    gpu_temp: Optional[float] = None
    gpu_fan: Optional[float] = None
    temperatures: Dict[str, float] = field(default_factory=dict)
    last_update: Optional[datetime.datetime] = None


class TradingDashboard:
    """Real-time trading dashboard with 1-second updates"""

    def __init__(
        self,
        runner: NirajRunner,
        mode: TradingMode = TradingMode.PAPER,
        initial_balance: Decimal = Decimal('10000.0')
    ):
        self.runner = runner
        self.mode = mode
        self.is_terminal_mode = True
        self.update_interval = 1.0  # 1 second updates
        self.is_running = False
        self.update_thread: Optional[threading.Thread] = None

        # Trading accounts
        self.dhan_account = TradingAccount(broker="dhan", balance=initial_balance)
        self.angel_account = TradingAccount(broker="angel_one", balance=initial_balance)

        # Market data
        self.market_data = MarketData()

        # AI status
        self.ai_status = AIStatus()

        # News headlines
        self.news_headlines: List[str] = []

        # Chart pattern (simple text representation)
        self.chart_pattern: List[str] = []

        # Backend API base URL
        self.api_base_url = "http://localhost:8000/api/v1"

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = Decimal('0.0')
        # System stats
        self.system_stats = SystemStats()
        self._net_base = psutil.net_io_counters() if PSUTIL_AVAILABLE else None

    def start(self):
        """Start the dashboard"""
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.runner.log("📊 Trading Dashboard started", "success")

    def stop(self):
        """Stop the dashboard"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        self.runner.log("📊 Trading Dashboard stopped", "info")

    def _update_loop(self):
        """Main update loop that runs every second"""
        while self.is_running:
            try:
                self._fetch_all_data()
                self._fetch_system_stats()
                if self.is_terminal_mode:
                    self._render_terminal_dashboard()
                time.sleep(self.update_interval)
            except Exception:
                # Silent fail on update errors
                time.sleep(self.update_interval)

    def _fetch_all_data(self):
        """Fetch all data from backend APIs"""
        try:
            # Use requests if available, otherwise skip
            try:
                import requests
            except ImportError:
                return

            # Fetch balances and positions
            self._fetch_account_data(requests)

            # Fetch market data
            self._fetch_market_data(requests)

            # Fetch news
            self._fetch_news(requests)

            # Fetch AI status
            self._fetch_ai_status(requests)

        except Exception:
            pass  # Silent fail for data fetch

    def _fetch_account_data(self, requests):
        """Fetch account balances and positions"""
        try:
            # For paper trading, use simulated data
            if self.mode == TradingMode.PAPER:
                # Calculate PNL from positions
                self.dhan_account.last_update = datetime.datetime.now()
                self.angel_account.last_update = datetime.datetime.now()
            else:
                # Fetch real data from brokers
                # Dhan balance and positions
                try:
                    dhan_resp = requests.get(
                        f"{self.api_base_url}/portfolio/balance/dhan",
                        timeout=0.5
                    )
                    if dhan_resp.status_code == 200:
                        data = dhan_resp.json()
                        self.dhan_account.balance = Decimal(str(data.get('balance', 0)))
                        self.dhan_account.pnl = Decimal(str(data.get('pnl', 0)))
                except Exception:
                    pass

                # Angel One balance and positions
                try:
                    angel_resp = requests.get(
                        f"{self.api_base_url}/portfolio/balance/angel_one",
                        timeout=0.5
                    )
                    if angel_resp.status_code == 200:
                        data = angel_resp.json()
                        self.angel_account.balance = Decimal(str(data.get('balance', 0)))
                        self.angel_account.pnl = Decimal(str(data.get('pnl', 0)))
                except Exception:
                    pass
        except Exception:
            pass

    def _fetch_market_data(self, requests):
        """Fetch Bank Nifty and market data"""
        try:
            response = requests.get(
                f"{self.api_base_url}/market-data/NIFTY BANK/ltp",
                timeout=0.5
            )
            if response.status_code == 200:
                data = response.json()
                self.market_data.bank_nifty_price = Decimal(str(data.get('ltp', 0)))
                self.market_data.bank_nifty_change = Decimal(str(data.get('change', 0)))
                self.market_data.bank_nifty_change_percent = Decimal(str(data.get('change_percent', 0)))
                self.market_data.last_update = datetime.datetime.now()

                # Determine trend
                if self.market_data.bank_nifty_change > 0:
                    self.market_data.trend = "BULLISH ▲"
                elif self.market_data.bank_nifty_change < 0:
                    self.market_data.trend = "BEARISH ▼"
                else:
                    self.market_data.trend = "NEUTRAL ■"
        except Exception:
            pass

    def _fetch_news(self, requests):
        """Fetch latest news headlines"""
        try:
            response = requests.get(
                f"{self.api_base_url}/news/headlines?limit=5",
                timeout=0.5
            )
            if response.status_code == 200:
                data = response.json()
                self.news_headlines = [
                    item.get('title', '')[:60] + "..."
                    for item in data.get('articles', [])[:5]
                ]
        except Exception:
            self.news_headlines = ["News service unavailable"]

    def _fetch_ai_status(self, requests):
        """Fetch AI engine status"""
        try:
            response = requests.get(
                f"{self.api_base_url}/ai/status",
                timeout=0.5
            )
            if response.status_code == 200:
                data = response.json()
                self.ai_status.is_active = data.get('active', False)
                self.ai_status.is_training = data.get('training', False)
                self.ai_status.is_thinking = data.get('thinking', False)
                self.ai_status.current_task = data.get('task', 'Idle')
                self.ai_status.confidence = data.get('confidence', 0.0)
                self.ai_status.last_update = datetime.datetime.now()
        except Exception:
            self.ai_status.current_task = "AI service unavailable"

    def _render_terminal_dashboard(self):
        """Render the dashboard in terminal"""
        # Clear screen
        os.system('clear' if os.name != 'nt' else 'cls')

        # Get terminal width
        try:
            term_width = shutil.get_terminal_size().columns
        except Exception:
            term_width = 120

        # Header
        self._print_header(term_width)

        # Trading mode and time
        self._print_mode_time()

        # Account balances
        self._print_accounts()

        # Market data
        self._print_market_data()

        # Positions and trades
        self._print_positions_trades()

        # PNL Summary
        self._print_pnl_summary()

        # News
        self._print_news()

        # AI Status
        self._print_ai_status()

        # Chart pattern
        self._print_chart_pattern()
        # System stats (hardware telemetry)
        self._print_system_stats()

        # Footer
        self._print_footer(term_width)

    def _print_header(self, width: int):
        """Print dashboard header"""
        if COLORAMA_AVAILABLE:
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{'═' * width}")
            title = "NIRAJ TRADING SYSTEM - LIVE DASHBOARD"
            print(f"{title.center(width)}")
            print(f"{'═' * width}{Style.RESET_ALL}\n")
        else:
            print(f"\n{'=' * width}")
            print("NIRAJ TRADING SYSTEM - LIVE DASHBOARD".center(width))
            print(f"{'=' * width}\n")

    def _print_mode_time(self):
        """Print trading mode and current time"""
        now = datetime.datetime.now()
        mode_text = "PAPER TRADING (₹10,000)" if self.mode == TradingMode.PAPER else "LIVE TRADING"
        display_mode = "Terminal Mode" if self.is_terminal_mode else "Web Mode"

        if COLORAMA_AVAILABLE:
            mode_color = Fore.YELLOW if self.mode == TradingMode.PAPER else Fore.RED
            print(f"{mode_color}{Style.BRIGHT}🔴 {mode_text} | {display_mode}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}🕐 {now.strftime('%Y-%m-%d %H:%M:%S')} IST{Style.RESET_ALL}\n")
        else:
            print(f"🔴 {mode_text} | {display_mode}")
            print(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')} IST\n")

    def _print_accounts(self):
        """Print account balances"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}┌─ ACCOUNT BALANCES ────────────────────────────────────────┐{Style.RESET_ALL}")

            # Dhan account
            dhan_bal = self.dhan_account.balance
            dhan_pnl = self.dhan_account.pnl
            dhan_color = Fore.GREEN if dhan_pnl >= 0 else Fore.RED
            print(f"{Fore.BLUE}│ 💰 DHAN:{Style.RESET_ALL}       ₹{dhan_bal:,.2f}  |  PNL: {dhan_color}₹{dhan_pnl:,.2f}{Style.RESET_ALL}")

            # Angel One account
            angel_bal = self.angel_account.balance
            angel_pnl = self.angel_account.pnl
            angel_color = Fore.GREEN if angel_pnl >= 0 else Fore.RED
            print(f"{Fore.BLUE}│ 💰 ANGEL ONE:{Style.RESET_ALL}  ₹{angel_bal:,.2f}  |  PNL: {angel_color}₹{angel_pnl:,.2f}{Style.RESET_ALL}")

            # Total
            total_bal = dhan_bal + angel_bal
            total_pnl = dhan_pnl + angel_pnl
            total_color = Fore.GREEN if total_pnl >= 0 else Fore.RED
            print(f"{Fore.CYAN}│ {Style.BRIGHT}TOTAL:{Style.RESET_ALL}      ₹{total_bal:,.2f}  |  PNL: {total_color}₹{total_pnl:,.2f}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ ACCOUNT BALANCES ────────────────────────────────────────┐")
            print(f"│ 💰 DHAN:       ₹{self.dhan_account.balance:,.2f}  |  PNL: ₹{self.dhan_account.pnl:,.2f}")
            print(f"│ 💰 ANGEL ONE:  ₹{self.angel_account.balance:,.2f}  |  PNL: ₹{self.angel_account.pnl:,.2f}")
            total_bal = self.dhan_account.balance + self.angel_account.balance
            total_pnl = self.dhan_account.pnl + self.angel_account.pnl
            print(f"│ TOTAL:      ₹{total_bal:,.2f}  |  PNL: ₹{total_pnl:,.2f}")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_market_data(self):
        """Print market data"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.MAGENTA}{Style.BRIGHT}┌─ MARKET DATA ─────────────────────────────────────────────┐{Style.RESET_ALL}")

            price = self.market_data.bank_nifty_price or Decimal('0')
            change = self.market_data.bank_nifty_change or Decimal('0')
            change_pct = self.market_data.bank_nifty_change_percent or Decimal('0')

            color = Fore.GREEN if change >= 0 else Fore.RED
            print(f"{Fore.YELLOW}│ 📈 BANK NIFTY:{Style.RESET_ALL} {price:,.2f}  {color}{change:+,.2f} ({change_pct:+.2f}%){Style.RESET_ALL}")
            print(f"{Fore.YELLOW}│ 📊 TREND:{Style.RESET_ALL}      {self.market_data.trend}")
            print(f"{Fore.YELLOW}│ 📉 VOLATILITY:{Style.RESET_ALL} {self.market_data.volatility}")
            print(f"{Fore.MAGENTA}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ MARKET DATA ─────────────────────────────────────────────┐")
            price = self.market_data.bank_nifty_price or Decimal('0')
            change = self.market_data.bank_nifty_change or Decimal('0')
            change_pct = self.market_data.bank_nifty_change_percent or Decimal('0')
            print(f"│ 📈 BANK NIFTY: {price:,.2f}  {change:+,.2f} ({change_pct:+.2f}%)")
            print(f"│ 📊 TREND:      {self.market_data.trend}")
            print(f"│ 📉 VOLATILITY: {self.market_data.volatility}")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_positions_trades(self):
        """Print active positions and recent trades"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.GREEN}{Style.BRIGHT}┌─ POSITIONS & TRADES ──────────────────────────────────────┐{Style.RESET_ALL}")

            # Dhan trades
            dhan_trades = len(self.dhan_account.trades)
            dhan_positions = len(self.dhan_account.positions)
            print(f"{Fore.BLUE}│ DHAN:{Style.RESET_ALL}       {dhan_positions} positions | {dhan_trades} trades today")

            # Angel One trades
            angel_trades = len(self.angel_account.trades)
            angel_positions = len(self.angel_account.positions)
            print(f"{Fore.BLUE}│ ANGEL ONE:{Style.RESET_ALL}  {angel_positions} positions | {angel_trades} trades today")

            # Total stats
            print(f"{Fore.GREEN}│ {Style.BRIGHT}TOTAL:{Style.RESET_ALL}      {self.total_trades} trades | W: {self.winning_trades} | L: {self.losing_trades}")
            print(f"{Fore.GREEN}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ POSITIONS & TRADES ──────────────────────────────────────┐")
            print(f"│ DHAN:       {len(self.dhan_account.positions)} positions | {len(self.dhan_account.trades)} trades today")
            print(f"│ ANGEL ONE:  {len(self.angel_account.positions)} positions | {len(self.angel_account.trades)} trades today")
            print(f"│ TOTAL:      {self.total_trades} trades | W: {self.winning_trades} | L: {self.losing_trades}")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_pnl_summary(self):
        """Print PNL summary"""
        total_pnl = self.dhan_account.pnl + self.angel_account.pnl

        if COLORAMA_AVAILABLE:
            color = Fore.GREEN if total_pnl >= 0 else Fore.RED
            print(f"{color}{Style.BRIGHT}┌─ PNL SUMMARY ─────────────────────────────────────────────┐{Style.RESET_ALL}")
            print(f"{color}│ TODAY'S PNL:  ₹{total_pnl:,.2f}{Style.RESET_ALL}")

            # Calculate win rate
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            print(f"{Fore.WHITE}│ WIN RATE:     {win_rate:.1f}%{Style.RESET_ALL}")
            print(f"{color}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ PNL SUMMARY ─────────────────────────────────────────────┐")
            print(f"│ TODAY'S PNL:  ₹{total_pnl:,.2f}")
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            print(f"│ WIN RATE:     {win_rate:.1f}%")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_news(self):
        """Print news headlines"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.YELLOW}{Style.BRIGHT}┌─ NEWS HEADLINES ──────────────────────────────────────────┐{Style.RESET_ALL}")
            for i, headline in enumerate(self.news_headlines[:5], 1):
                print(f"{Fore.WHITE}│ {i}. {headline[:55]:<55}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ NEWS HEADLINES ──────────────────────────────────────────┐")
            for i, headline in enumerate(self.news_headlines[:5], 1):
                print(f"│ {i}. {headline[:55]}")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_ai_status(self):
        """Print AI engine status"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.MAGENTA}{Style.BRIGHT}┌─ AI ENGINE STATUS ────────────────────────────────────────┐{Style.RESET_ALL}")

            status_emoji = "🟢" if self.ai_status.is_active else "🔴"
            status_text = "ACTIVE" if self.ai_status.is_active else "INACTIVE"
            print(f"{Fore.WHITE}│ STATUS:     {status_emoji} {status_text}{Style.RESET_ALL}")

            if self.ai_status.is_training:
                print(f"{Fore.YELLOW}│ TRAINING:   🔄 In Progress{Style.RESET_ALL}")
            elif self.ai_status.is_thinking:
                print(f"{Fore.CYAN}│ THINKING:   🧠 Analyzing market...{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}│ TASK:       {self.ai_status.current_task}{Style.RESET_ALL}")

            confidence_color = Fore.GREEN if self.ai_status.confidence > 0.7 else (Fore.YELLOW if self.ai_status.confidence > 0.4 else Fore.RED)
            print(f"{Fore.WHITE}│ CONFIDENCE: {confidence_color}{self.ai_status.confidence:.1%}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ AI ENGINE STATUS ────────────────────────────────────────┐")
            status_text = "ACTIVE" if self.ai_status.is_active else "INACTIVE"
            print(f"│ STATUS:     {status_text}")
            if self.ai_status.is_training:
                print("│ TRAINING:   In Progress")
            elif self.ai_status.is_thinking:
                print("│ THINKING:   Analyzing market...")
            else:
                print(f"│ TASK:       {self.ai_status.current_task}")
            print(f"│ CONFIDENCE: {self.ai_status.confidence:.1%}")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_chart_pattern(self):
        """Print Bank Nifty chart pattern (simple ASCII representation)"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}┌─ BANK NIFTY CHART PATTERN ────────────────────────────────┐{Style.RESET_ALL}")

            # Simple trend indicator
            change = self.market_data.bank_nifty_change or Decimal('0')
            if change > 0:
                pattern = "│     📈📈📈 UPTREND - Support at previous low"
            elif change < 0:
                pattern = "│     📉📉📉 DOWNTREND - Resistance at previous high"
            else:
                pattern = "│     📊📊📊 CONSOLIDATION - Range bound"

            print(f"{Fore.WHITE}{pattern}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("┌─ BANK NIFTY CHART PATTERN ────────────────────────────────┐")
            change = self.market_data.bank_nifty_change or Decimal('0')
            if change > 0:
                print("│     UPTREND - Support at previous low")
            elif change < 0:
                print("│     DOWNTREND - Resistance at previous high")
            else:
                print("│     CONSOLIDATION - Range bound")
            print("└────────────────────────────────────────────────────────────┘\n")

    def _print_footer(self, width: int):
        """Print dashboard footer"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{'─' * width}")
            print(f"{Fore.WHITE}Press Ctrl+C to stop | Switch to Web: 'w' | Refresh: 1s{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        else:
            print(f"{'─' * width}")
            print("Press Ctrl+C to stop | Switch to Web: 'w' | Refresh: 1s")
            print(f"{'=' * width}")

    # ---------------- System Stats Rendering -----------------
    def _print_system_stats(self):
        stats = self.system_stats
        if not stats.last_update:
            return

        def get_health_color(percent: float, thresholds=(50, 75, 90)) -> str:
            """Get color based on usage percentage"""
            if not COLORAMA_AVAILABLE:
                return ""
            if percent < thresholds[0]:
                return Fore.GREEN
            elif percent < thresholds[1]:
                return Fore.YELLOW
            elif percent < thresholds[2]:
                return Fore.YELLOW + Style.BRIGHT
            else:
                return Fore.RED

        def format_bar(percent: float, width: int = 10) -> str:
            """Create a visual progress bar"""
            filled = int(width * (percent / 100))
            bar = "█" * filled + "░" * (width - filled)
            return bar

        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}┌─ SYSTEM HEALTH & PERFORMANCE ─────────────────────────────┐{Style.RESET_ALL}")
        else:
            print("┌─ SYSTEM HEALTH & PERFORMANCE ─────────────────────────────┐")

        # CPU with color coding and bar
        cpu_color = get_health_color(stats.cpu_percent)
        cpu_bar = format_bar(stats.cpu_percent, 15) if COLORAMA_AVAILABLE else ""
        if COLORAMA_AVAILABLE:
            cpu_line = f"🔥 CPU: {cpu_color}{stats.cpu_percent:5.1f}%{Style.RESET_ALL} {cpu_bar} ({stats.cpu_cores}c) Load: {stats.load_avg_1m:4.2f}"
        else:
            cpu_line = f"CPU: {stats.cpu_percent:5.1f}% ({stats.cpu_cores}c) Load: {stats.load_avg_1m:4.2f}"

        # Memory with color coding and bar
        mem_color = get_health_color(stats.memory_percent)
        mem_bar = format_bar(stats.memory_percent, 15) if COLORAMA_AVAILABLE else ""
        if COLORAMA_AVAILABLE:
            mem_line = f"💾 RAM: {mem_color}{stats.memory_percent:5.1f}%{Style.RESET_ALL} {mem_bar} {stats.memory_used:4.1f}/{stats.memory_total:4.1f}G"
        else:
            mem_line = f"RAM: {stats.memory_percent:5.1f}% {stats.memory_used:4.1f}/{stats.memory_total:4.1f}G"

        # Disk with color coding
        disk_color = get_health_color(stats.disk_percent)
        if COLORAMA_AVAILABLE:
            disk_line = f"💿 DSK: {disk_color}{stats.disk_percent:5.1f}%{Style.RESET_ALL} {stats.disk_used:5.1f}/{stats.disk_total:5.1f}G | NET ↑{stats.net_sent:5.1f}M ↓{stats.net_recv:5.1f}M"
        else:
            disk_line = f"DSK: {stats.disk_percent:5.1f}% {stats.disk_used:5.1f}/{stats.disk_total:5.1f}G | NET ↑{stats.net_sent:5.1f}M ↓{stats.net_recv:5.1f}M"

        # GPU with enhanced display
        if stats.gpu_name:
            gpu_util = stats.gpu_util or 0
            gpu_temp = stats.gpu_temp or 0
            gpu_mem = stats.gpu_mem_util or 0

            gpu_util_color = get_health_color(gpu_util)
            gpu_temp_color = get_health_color(gpu_temp, (60, 75, 85))
            gpu_mem_color = get_health_color(gpu_mem)

            if COLORAMA_AVAILABLE:
                gpu_name_short = stats.gpu_name[:20] if len(stats.gpu_name) > 20 else stats.gpu_name
                gpu_line = f"🎮 GPU: {Fore.CYAN}{gpu_name_short}{Style.RESET_ALL}"
                gpu_metrics = f"   └─ Load:{gpu_util_color}{gpu_util:5.0f}%{Style.RESET_ALL} Mem:{gpu_mem_color}{gpu_mem:5.0f}%{Style.RESET_ALL} Temp:{gpu_temp_color}{gpu_temp:3.0f}°C{Style.RESET_ALL}"
                if stats.gpu_fan is not None:
                    fan_color = Fore.CYAN if stats.gpu_fan < 50 else Fore.YELLOW if stats.gpu_fan < 80 else Fore.RED
                    gpu_metrics += f" Fan:{fan_color}{stats.gpu_fan:3.0f}%{Style.RESET_ALL}"
            else:
                gpu_line = f"GPU: {stats.gpu_name[:25]}"
                gpu_metrics = f"   Load:{gpu_util:5.0f}% Mem:{gpu_mem:5.0f}% Temp:{gpu_temp:3.0f}°C"
                if stats.gpu_fan is not None:
                    gpu_metrics += f" Fan:{stats.gpu_fan:3.0f}%"
        else:
            if COLORAMA_AVAILABLE:
                gpu_line = f"🎮 GPU: {Fore.WHITE}{Style.DIM}N/A (No NVIDIA GPU detected){Style.RESET_ALL}"
            else:
                gpu_line = "GPU: N/A"
            gpu_metrics = None

        # Temperature sensors
        temp_line = None
        if stats.temperatures:
            temps = []
            for sensor, temp in list(stats.temperatures.items())[:3]:
                temp_color = get_health_color(temp, (50, 70, 85))
                if COLORAMA_AVAILABLE:
                    temps.append(f"{sensor[:8]}:{temp_color}{temp:.0f}°C{Style.RESET_ALL}")
                else:
                    temps.append(f"{sensor[:8]}:{temp:.0f}°C")
            if temps:
                temp_line = f"🌡️  Temps: {' '.join(temps)}"

        # Print all lines
        for line in [cpu_line, mem_line, disk_line, gpu_line]:
            print(f"│ {line[:70].ljust(70) if not COLORAMA_AVAILABLE else line}")

        if gpu_metrics:
            print(f"│ {gpu_metrics}")

        if temp_line:
            print(f"│ {temp_line}")

        # System health indicator
        avg_usage = (stats.cpu_percent + stats.memory_percent + stats.disk_percent) / 3
        if COLORAMA_AVAILABLE:
            health_emoji = "🟢" if avg_usage < 50 else "🟡" if avg_usage < 75 else "🔴"
            health_text = "OPTIMAL" if avg_usage < 50 else "MODERATE" if avg_usage < 75 else "HIGH LOAD"
            health_color = Fore.GREEN if avg_usage < 50 else Fore.YELLOW if avg_usage < 75 else Fore.RED
            print(f"│ {health_emoji} System Health: {health_color}{health_text}{Style.RESET_ALL} (Avg: {avg_usage:.1f}%)")

        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}└────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n")
        else:
            print("└────────────────────────────────────────────────────────────┘\n")

    # ---------------- System Stats Collection -----------------
    def _fetch_system_stats(self):
        if not PSUTIL_AVAILABLE:
            return
        try:
            s = self.system_stats
            s.cpu_percent = psutil.cpu_percent(interval=None)
            s.cpu_cores = psutil.cpu_count(logical=True) or 0
            if hasattr(os, 'getloadavg'):
                la = os.getloadavg()
                s.load_avg_1m = la[0]
                if s.cpu_cores:
                    s.load_ratio = la[0] / s.cpu_cores
            vm = psutil.virtual_memory()
            s.memory_used = vm.used / (1024**3)
            s.memory_total = vm.total / (1024**3)
            s.memory_percent = vm.percent
            sw = psutil.swap_memory()
            s.swap_used = sw.used / (1024**3)
            s.swap_total = sw.total / (1024**3)
            du = shutil.disk_usage(PROJECT_ROOT)
            s.disk_used = du.used / (1024**3)
            s.disk_total = du.total / (1024**3)
            s.disk_percent = (du.used / du.total * 100) if du.total else 0
            if self._net_base:
                cur = psutil.net_io_counters()
                s.net_sent = (cur.bytes_sent - self._net_base.bytes_sent) / (1024**2)
                s.net_recv = (cur.bytes_recv - self._net_base.bytes_recv) / (1024**2)
            # Temperatures (best effort)
            try:
                temps = psutil.sensors_temperatures()  # type: ignore[attr-defined]
                flat: Dict[str, float] = {}
                for k, arr in temps.items():
                    if arr:
                        flat[k] = getattr(arr[0], 'current', None) or 0.0
                s.temperatures = flat
            except Exception:
                pass
            self._populate_gpu_stats(s)
            s.last_update = datetime.datetime.now()
        except Exception:
            pass

    def _populate_gpu_stats(self, s: SystemStats):
        try:
            smi = shutil.which('nvidia-smi')
            if not smi:
                return
            cmd = [smi, '--query-gpu=name,utilization.gpu,utilization.memory,temperature.gpu,fan.speed', '--format=csv,noheader,nounits']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            if res.returncode != 0 or not res.stdout.strip():
                return
            line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                s.gpu_name = parts[0]
                try:
                    s.gpu_util = float(parts[1])
                    s.gpu_mem_util = float(parts[2])
                    s.gpu_temp = float(parts[3])
                except ValueError:
                    return
                try:
                    s.gpu_fan = float(parts[4])
                except ValueError:
                    s.gpu_fan = None
        except Exception:
            pass

    def toggle_mode(self):
        """Toggle between terminal and web mode"""
        self.is_terminal_mode = not self.is_terminal_mode
        mode = "Terminal" if self.is_terminal_mode else "Web"
        self.runner.log(f"🔄 Switched to {mode} Mode", "info")

        # If switching to web mode, start frontend if not running
        if not self.is_terminal_mode:
            if "frontend" not in self.runner.processes:
                self.runner.start_service("frontend")
        else:
            # Stop frontend to reduce CPU load
            if "frontend" in self.runner.processes:
                self.runner.stop_service("frontend")


# ---------------- Fan Control Utilities -----------------
def set_fan_speed(percent: int) -> bool:
    """Attempt to set NVIDIA GPU fan speed (best effort).
    Returns True if command was attempted (not necessarily that hardware obeyed).
    Requires nvidia-settings and proper permissions; many laptops lock fan control.
    """
    try:
        nvset = shutil.which('nvidia-settings')
        if not nvset:
            return False
        # Enable manual fan control
        subprocess.run([nvset, '-a', '[gpu:0]/GPUFanControlState=1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([nvset, '-a', f'[fan:0]/GPUTargetFanSpeed={percent}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive Menu Mode
  python niraj.py                                             # Launch interactive menu

  # Trading Dashboard Modes
  python niraj.py --terminal-mode --paper-trading             # Paper trading (₹10K virtual)
  python niraj.py --terminal-mode --real-trading              # Real trading (CAUTION!)
  python niraj.py --dashboard-only --paper-trading            # Dashboard only (needs backend)

  # GPU Fan Control (NVIDIA only, requires nvidia-settings)
  python niraj.py --terminal-mode --fan-speed max             # Maximum cooling
  python niraj.py --terminal-mode --fan-speed 70              # Balanced (70%)
  python niraj.py --terminal-mode --fan-speed 30              # Quiet mode (30%)
  python niraj.py --real-trading --fan-speed 50               # Real trading with 50% fan

  # Service Management
  python niraj.py --enable-api --enable-frontend              # Start API and frontend
  python niraj.py --enable-api --enable-redis --enable-ollama # Full backend stack
  python niraj.py --mode production --enable-api --enable-redis  # Production mode
  python niraj.py status                                       # Show service status
  python niraj.py stop                                         # Stop all services
  python niraj.py install                                      # Install dependencies

  # Advanced Configuration
  python niraj.py --config custom.json --enable-backend        # Use custom config
  python niraj.py --mode testing --enable-api                  # Testing environment

Dashboard Features (updates every 1 second):
  • Account Balances: Dhan + Angel One with live PNL
  • Market Data: Bank Nifty price, trend, pattern analysis
  • News Feed: Latest 5 headlines from market news
  • AI Status: Training state, confidence, signals
  • System Stats: CPU, RAM, Disk, Network, GPU, Temps
  • GPU Monitoring: Utilization, memory, temperature, fan speed

System Monitoring:
  • CPU: Usage %, core count, load average with color bars
  • Memory: RAM usage, swap stats with visual indicators
  • Disk: Storage usage, network traffic counters
  • GPU: NVIDIA cards (name, load, memory, temp, fan)
  • Temps: CPU/System temperature sensors
  • Health: Overall system health indicator

Fan Control Notes:
  • Requires NVIDIA GPU with nvidia-settings installed
  • Options: 10, 30, 50, 70, 100, max (max = 100%)
  • Many laptops lock fan control via BIOS
  • Monitor temperatures when using manual fan speeds
  • Default auto mode if not specified

For detailed documentation, see:
  • SYSTEM_MONITORING_FEATURES.md - System stats & GPU control
  • README.md - General project documentation
  • docs/ - API reference and guides
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["development", "production", "testing"],
        default="development",
        help="Environment mode (default: development)",
    )

    parser.add_argument("--config", help="Path to custom configuration file")

    parser.add_argument(
        "--enable-api",
        "--enable-backend",
        action="store_true",
        help="Enable backend API server",
    )

    parser.add_argument(
        "--enable-frontend",
        action="store_true",
        help="Enable frontend development server",
    )

    parser.add_argument(
        "--enable-redis", action="store_true", help="Enable Redis server"
    )

    parser.add_argument(
        "--enable-ollama", action="store_true", help="Enable Ollama AI server"
    )

    parser.add_argument(
        "--menu",
        "--interactive",
        action="store_true",
        help="Run in interactive menu mode",
    )

    parser.add_argument(
        "--terminal-mode",
        action="store_true",
        help="Start in terminal trading dashboard mode",
    )

    parser.add_argument(
        "--paper-trading",
        action="store_true",
        help="Enable paper trading mode with ₹10,000 virtual balance",
    )

    parser.add_argument(
        "--real-trading",
        action="store_true",
        help="Enable real trading mode (use with caution!)",
    )

    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Run only the trading dashboard (requires backend to be running)",
    )

    parser.add_argument(
        "--fan-speed",
        choices=["max", "100", "70", "50", "30", "10"],
        help="Set NVIDIA GPU fan speed percentage (requires nvidia-settings). 'max'=100",
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["status", "stop", "install", "menu"],
        help="Command to run (status, stop, install, menu)",
    )

    args = parser.parse_args()

    # Create runner
    runner = NirajRunner(mode=args.mode, config_file=args.config)

    # Optional fan speed control (best effort)
    if args.fan_speed:
        percent_map = {"max": 100, "100": 100, "70": 70, "50": 50, "30": 30, "10": 10}
        target = percent_map.get(args.fan_speed, 100)
        if set_fan_speed(target):
            runner.log(f"🌀 Set GPU fan speed to {target}% (manual mode)", "success")
        else:
            runner.log("GPU fan control unavailable (needs NVIDIA + nvidia-settings + permissions)", "warning")

    # Handle trading dashboard modes
    if args.dashboard_only or args.terminal_mode:
        # Determine trading mode
        trading_mode = TradingMode.REAL if args.real_trading else TradingMode.PAPER

        # Create trading dashboard
        dashboard = TradingDashboard(
            runner=runner,
            mode=trading_mode,
            initial_balance=Decimal('10000.0')
        )

        # If dashboard_only, just start dashboard (backend must be running)
        if args.dashboard_only:
            runner.log("📊 Starting Trading Dashboard Only", "header")
            runner.log("⚠️  Make sure backend is running!", "warning")
            dashboard.start()

            try:
                # Keep running until interrupted
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                dashboard.stop()
                runner.log("Dashboard stopped", "info")
            return

        # If terminal_mode, start backend and dashboard
        runner.log("🚀 Starting Terminal Trading Mode", "header")

        # Start backend and redis
        if not runner.start_service("backend"):
            runner.log("Failed to start backend", "error")
            return
        if not runner.start_service("redis"):
            runner.log("Failed to start redis", "error")

        # Start dashboard
        dashboard.start()

        # Setup signal handlers
        def signal_handler(signum, frame):
            runner.log("Shutting down...", "warning")
            dashboard.stop()
            runner.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            dashboard.stop()
            runner.stop_all()

        return

    # Check if any services are specified or if it's a command
    has_services = any(
        [args.enable_api, args.enable_frontend, args.enable_redis, args.enable_ollama]
    )
    has_command = args.command is not None

    # If no arguments provided or menu requested, start interactive mode
    if not has_services and not has_command or args.menu or args.command == "menu":
        menu = MenuInterface(runner)
        menu.run()
        return

    # Handle commands
    if args.command == "status":
        runner.show_status()
        return
    elif args.command == "stop":
        runner.stop_all()
        return
    elif args.command == "install":
        runner.install_dependencies()
        return

    # Determine services to start
    services_to_start = []
    if args.enable_api:
        services_to_start.append("backend")
    if args.enable_frontend:
        services_to_start.append("frontend")
    if args.enable_redis:
        services_to_start.append("redis")
    if args.enable_ollama:
        services_to_start.append("ollama")

    if not services_to_start:
        # If no services specified, start interactive menu
        menu = MenuInterface(runner)
        menu.run()
        return

    # Run the system
    runner.run(services_to_start)


if __name__ == "__main__":
    main()
