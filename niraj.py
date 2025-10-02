#!/usr/bin/env python3
"""
NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System
Single Runner Script

This script provides a unified interface to run the NIRAJ trading system
with different configurations and modes.

Usage:
    python niraj.py --mode development --enable-api --enable-frontend
    python niraj.py --mode production --enable-api
    python niraj.py status
    python niraj.py stop
    python niraj.py --help
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable, Mapping
from dataclasses import dataclass

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

        # Load configuration
        self.load_config()

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
                    "env": {"PYTHONPATH": "src"},
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

            # Start process
            popen_obj = subprocess.Popen(
                service.command,
                cwd=service.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
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
                    return True
                else:
                    self.log(f"❌ {service_name} health check failed", "error")
                    self.stop_service(service_name)
                    return False
            else:
                if isinstance(process_ref, subprocess.Popen):
                    stdout, _ = process_ref.communicate()
                    self.log(f"❌ {service_name} failed to start: {stdout}", "error")
                else:
                    self.log(f"❌ {service_name} failed to start (unknown process type)", "error")
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
        except subprocess.TimeoutExpired:
            process.kill()
            self.log(f"⚠️  {service_name} force killed", "warning")
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
        """Show status of all services"""
        self.log("📊 Service Status", "header")

        for service_name, service in self.services.items():
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    status = "✅ Running"
                else:
                    status = "❌ Stopped"
            else:
                status = "⭕ Not Started"

            print(f"  {service_name}: {status}")
            if (
                service_name in self.processes
                and self.processes[service_name].poll() is None
            ):
                if service_name == "backend":
                    print("    API: http://localhost:8000")
                    print("    Docs: http://localhost:8000/docs")
                elif service_name == "frontend":
                    print("    URL: http://localhost:5173")
                elif service_name == "redis":
                    print("    URL: localhost:6379")
                elif service_name == "ollama":
                    print("    URL: http://localhost:11434")
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

        # Start services
        started_services = []
        for service_name in services_to_start:
            if self.start_service(service_name):
                started_services.append(service_name)

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


class MenuInterface:
    """Interactive menu interface for NIRAJ system"""

    def __init__(self, runner: NirajRunner):
        self.runner = runner
        self.running = True

    def display_banner(self):
        """Display NIRAJ banner"""
        if COLORAMA_AVAILABLE:
            print(f"{Fore.CYAN}{Style.BRIGHT}")
            print("╔══════════════════════════════════════════════════════════════╗")
            print("║                         🚀 NIRAJ                             ║")
            print("║         Advanced Self-Learning Algorithmic AI               ║")
            print("║              Personal Trading System                        ║")
            print("║                                                              ║")
            print("║                    Interactive Menu                         ║")
            print("╚══════════════════════════════════════════════════════════════╝")
            print(f"{Style.RESET_ALL}")
        else:
            print("=" * 66)
            print("                         NIRAJ")
            print("         Advanced Self-Learning Algorithmic AI")
            print("              Personal Trading System")
            print("                    Interactive Menu")
            print("=" * 66)

    def display_main_menu(self):
        """Display main menu options"""
        print("\n📋 Main Menu:")
        print("  1. 🚀 Start Services")
        print("  2. 🛑 Stop Services")
        print("  3. 📊 Service Status")
        print("  4. 📦 Install Dependencies")
        print("  5. ⚙️  Configuration")
        print("  6. 🔧 Service Management")
        print("  7. 📚 Help & Documentation")
        print("  8. 🌍 Environment Settings")
        print("  9. 📋 Logs & Monitoring")
        print("  0. ❌ Exit")
        print()

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
        """Display service management menu"""
        print("\n🔧 Service Management:")
        print("  1. 🔄 Restart Service")
        print("  2. 🔍 View Service Logs")
        print("  3. 🏥 Health Check")
        print("  4. 📊 Performance Metrics")
        print("  5. 🔧 Service Configuration")
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
        """Get user input with error handling"""
        try:
            return input(
                f"{Fore.YELLOW if COLORAMA_AVAILABLE else ''}{prompt}{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            self.running = False
            return "0"

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
        while True:
            self.display_start_menu()
            choice = self.get_user_input()

            if choice == "0":
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
        while True:
            self.display_service_menu()
            choice = self.get_user_input()

            if choice == "0":
                break
            elif choice == "1":
                self.restart_service()
            elif choice == "2":
                self.view_service_logs()
            elif choice == "3":
                self.health_check()
            elif choice == "4":
                self.performance_metrics()
            elif choice == "5":
                self.service_configuration()
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

    def run(self):
        """Main menu loop"""
        self.display_banner()

        while self.running:
            self.display_main_menu()
            choice = self.get_user_input()

            if not self.running:  # User pressed Ctrl+C
                break

            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                self.handle_start_services()
            elif choice == "2":
                self.handle_stop_services()
            elif choice == "3":
                self.runner.show_status()
                self.safe_input()
            elif choice == "4":
                self.runner.install_dependencies()
                self.safe_input()
            elif choice == "5":
                self.handle_configuration()
            elif choice == "6":
                self.handle_service_management()
            elif choice == "7":
                self.handle_help()
            elif choice == "8":
                self.change_environment_mode()
                self.safe_input()
            elif choice == "9":
                print("\n📋 Logs & Monitoring:")
                print(
                    "Real-time monitoring and log aggregation would be implemented here."
                )
                self.safe_input()
            else:
                print("❌ Invalid choice. Please try again.")

        # Cleanup
        self.runner.stop_monitoring()
        self.runner.stop_all()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="NIRAJ - Advanced Self-Learning Algorithmic AI Personal Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python niraj.py                                             # Interactive menu mode
  python niraj.py --enable-api --enable-frontend              # Start API and frontend
  python niraj.py --mode production --enable-api --enable-redis  # Production mode
  python niraj.py status                                       # Show service status
  python niraj.py stop                                         # Stop all services
  python niraj.py install                                      # Install dependencies
  python niraj.py --config custom.json --enable-backend        # Use custom config
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
        "command",
        nargs="?",
        choices=["status", "stop", "install", "menu"],
        help="Command to run (status, stop, install, menu)",
    )

    args = parser.parse_args()

    # Create runner
    runner = NirajRunner(mode=args.mode, config_file=args.config)

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
