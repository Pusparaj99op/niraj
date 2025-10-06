#!/usr/bin/env python3
"""
RAG Training Orchestrator for NIRAJ Trading System

This module handles batch processing of RAG JSON files for training the Ollama Gemma3 model.
Provides real-time progress tracking, system monitoring, and comprehensive status reporting.

Features:
  • Batch processing of bank stock RAG JSON files
  • Real-time progress bars and status updates
  • System resource monitoring (CPU, GPU, Memory, Storage)
  • GPU temperature and fan speed monitoring
  • File-level tracking (pending, in-progress, completed, failed)
  • Error handling and retry mechanisms
  • Performance metrics and statistics
"""

import asyncio
import atexit
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil
import structlog

try:  # Optional GPU monitoring dependency
    import pynvml  # type: ignore
    PYNVML_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency optional at runtime
    pynvml = None  # type: ignore
    PYNVML_AVAILABLE = False

_NVML_INITIALIZED = False


def _shutdown_nvml():
    """Ensure NVML is shut down cleanly on process exit."""
    global _NVML_INITIALIZED
    if not PYNVML_AVAILABLE or not _NVML_INITIALIZED:
        return

    try:
        pynvml.nvmlShutdown()  # type: ignore[union-attr]
    except Exception:  # pragma: no cover - best effort shutdown
        pass
    finally:
        _NVML_INITIALIZED = False


# Configure logging
logger = structlog.get_logger(__name__)


class FileStatus(str, Enum):
    """Status of individual RAG file processing"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileProcessingInfo:
    """Information about a file being processed"""
    filename: str
    filepath: str
    status: FileStatus = FileStatus.PENDING
    file_size_mb: float = 0.0
    entries_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_seconds: float = 0.0
    error_message: Optional[str] = None
    ingested_items: int = 0
    success_rate: float = 0.0


@dataclass
class SystemStats:
    """System resource statistics"""
    cpu_percent: float = 0.0
    cpu_temp: Optional[float] = None
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    gpu_name: Optional[str] = None
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_memory_percent: float = 0.0
    gpu_temp: Optional[float] = None
    gpu_fan_speed: Optional[int] = None
    gpu_utilization: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TrainingProgress:
    """Overall training progress"""
    total_files: int = 0
    pending_files: int = 0
    in_progress_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_entries_processed: int = 0
    total_entries_ingested: int = 0
    overall_progress_percent: float = 0.0
    start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    elapsed_time_seconds: float = 0.0


class SystemMonitor:
    """Monitor system resources including GPU"""

    def __init__(self):
        self.has_gpu = self._check_gpu_available()
        self.gpu_count = self._get_gpu_count() if self.has_gpu else 0
        self.pynvml_available = False

        if self.has_gpu and PYNVML_AVAILABLE:
            self.pynvml_available = self._initialize_nvml()

    def _initialize_nvml(self) -> bool:
        """Initialize NVML once and register shutdown hook."""
        global _NVML_INITIALIZED

        if not PYNVML_AVAILABLE:
            return False

        if _NVML_INITIALIZED:
            return True

        try:
            pynvml.nvmlInit()  # type: ignore[union-attr]
            _NVML_INITIALIZED = True
            atexit.register(_shutdown_nvml)
            return True
        except Exception as exc:  # pragma: no cover - hardware specific
            logger.warning("NVML initialization failed", error=str(exc))
            return False

    def _check_gpu_available(self) -> bool:
        """Check if NVIDIA GPU is available"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _get_gpu_count(self) -> int:
        """Get number of GPUs"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n'))
            return 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return 0

    def get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try different sensor names
                    for sensor_name in ['coretemp', 'k10temp', 'cpu_thermal', 'cpu-thermal']:
                        if sensor_name in temps:
                            entries = temps[sensor_name]
                            if entries:
                                return round(entries[0].current, 1)
            return None
        except Exception:
            return None

    def _clean_numeric(self, value: str) -> Optional[float]:
        """Convert nvidia-smi numeric fields to floats, handling N/A markers."""
        cleaned = value.strip().strip('[]')
        if not cleaned or cleaned.upper() == 'N/A':
            return None

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _get_gpu_stats_via_nvml(self) -> Optional[Dict[str, Any]]:
        """Retrieve GPU metrics using pynvml if available."""
        if not self.pynvml_available or not PYNVML_AVAILABLE:
            return None

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # type: ignore[union-attr]
            raw_name = pynvml.nvmlDeviceGetName(handle)  # type: ignore[union-attr]
            name = raw_name.decode('utf-8') if isinstance(raw_name, bytes) else str(raw_name)

            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)  # type: ignore[union-attr]
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)  # type: ignore[union-attr]
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)  # type: ignore[union-attr]

            fan_speed = None
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)  # type: ignore[union-attr]
            except Exception:  # pragma: no cover - some laptops report unsupported
                fan_speed = None

            memory_total_mb = mem_info.total / (1024 ** 2)
            memory_used_mb = mem_info.used / (1024 ** 2)

            return {
                'name': name,
                'memory_used_mb': round(memory_used_mb, 2),
                'memory_total_mb': round(memory_total_mb, 2),
                'memory_percent': round((memory_used_mb / memory_total_mb) * 100, 1) if memory_total_mb else 0.0,
                'temperature': float(temp),
                'fan_speed': fan_speed,
                'utilization': float(utilization.gpu),
            }
        except Exception as exc:  # pragma: no cover - runtime specific
            logger.debug("pynvml GPU stats failed, falling back to nvidia-smi", error=str(exc))
            return None

    def _get_gpu_stats_via_nvidia_smi(self) -> Optional[Dict[str, Any]]:
        """Fallback GPU stats collection via nvidia-smi command."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.used,memory.total,temperature.gpu,fan.speed,utilization.gpu",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            lines = result.stdout.strip().split('\n')
            if not lines:
                return None

            parts = [p.strip() for p in lines[0].split(',')]
            if len(parts) < 6:
                return None

            memory_used = self._clean_numeric(parts[1])
            memory_total = self._clean_numeric(parts[2])
            temperature = self._clean_numeric(parts[3])
            fan_speed = self._clean_numeric(parts[4])
            utilization = self._clean_numeric(parts[5])

            memory_percent = 0.0
            if memory_used is not None and memory_total not in (None, 0.0):
                memory_percent = round((memory_used / memory_total) * 100, 1)

            return {
                'name': parts[0],
                'memory_used_mb': memory_used or 0.0,
                'memory_total_mb': memory_total or 0.0,
                'memory_percent': memory_percent,
                'temperature': temperature,
                'fan_speed': fan_speed,
                'utilization': utilization,
            }
        except (subprocess.SubprocessError, ValueError, IndexError):
            return None

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU statistics using pynvml first, then nvidia-smi fallback."""
        if not self.has_gpu:
            return {}

        stats = self._get_gpu_stats_via_nvml()
        if stats:
            return stats

        stats = self._get_gpu_stats_via_nvidia_smi()
        return stats or {}

    def get_system_stats(self) -> SystemStats:
        """Get comprehensive system statistics"""
        stats = SystemStats()

        try:
            # CPU stats
            stats.cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)
            stats.cpu_temp = self.get_cpu_temperature()

            # Memory stats
            memory = psutil.virtual_memory()
            stats.memory_percent = round(memory.percent, 1)
            stats.memory_used_gb = round(memory.used / (1024 ** 3), 2)
            stats.memory_total_gb = round(memory.total / (1024 ** 3), 2)

            # Disk stats
            disk = psutil.disk_usage('/')
            stats.disk_percent = round(disk.percent, 1)
            stats.disk_used_gb = round(disk.used / (1024 ** 3), 2)
            stats.disk_total_gb = round(disk.total / (1024 ** 3), 2)

            # GPU stats
            if self.has_gpu:
                gpu_stats = self.get_gpu_stats()
                if gpu_stats:
                    stats.gpu_name = gpu_stats.get('name')
                    stats.gpu_memory_used_mb = gpu_stats.get('memory_used_mb', 0.0)
                    stats.gpu_memory_total_mb = gpu_stats.get('memory_total_mb', 0.0)
                    stats.gpu_memory_percent = gpu_stats.get('memory_percent', 0.0)
                    stats.gpu_temp = gpu_stats.get('temperature')
                    stats.gpu_fan_speed = gpu_stats.get('fan_speed')
                    stats.gpu_utilization = gpu_stats.get('utilization')

        except Exception as e:
            logger.error("Failed to get system stats", error=str(e))

        return stats


class RAGTrainingOrchestrator:
    """
    Orchestrates RAG training with Ollama Gemma3 model
    Handles batch processing, progress tracking, and system monitoring
    """

    def __init__(self, rag_json_dir: str, model_name: str = "gemma3:4b-it-q4_K_M"):
        self.rag_json_dir = Path(rag_json_dir)
        self.model_name = model_name
        self.system_monitor = SystemMonitor()

        # Processing state
        self.files: List[FileProcessingInfo] = []
        self.progress = TrainingProgress()
        self.is_running = False
        self.is_paused = False

        # Configuration
        self.batch_size = 10  # Process entries in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds

        logger.info(
            "RAG Training Orchestrator initialized",
            rag_dir=str(self.rag_json_dir),
            model=self.model_name
        )

    def discover_files(self) -> List[FileProcessingInfo]:
        """Discover all RAG JSON files in directory"""
        files = []

        try:
            if not self.rag_json_dir.exists():
                logger.error("RAG JSON directory not found", path=str(self.rag_json_dir))
                return files

            # Find all *_rag.json files
            json_files = list(self.rag_json_dir.glob("*_rag.json"))

            for json_file in sorted(json_files):
                try:
                    file_size_mb = round(json_file.stat().st_size / (1024 ** 2), 2)

                    # Try to count entries
                    entries_count = 0
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, dict):
                                # Handle different JSON structures
                                if 'data' in data and isinstance(data['data'], list):
                                    entries_count = len(data['data'])
                                elif 'entries' in data and isinstance(data['entries'], list):
                                    entries_count = len(data['entries'])
                                elif 'records' in data and isinstance(data['records'], list):
                                    entries_count = len(data['records'])
                                else:
                                    # Count all list values
                                    for value in data.values():
                                        if isinstance(value, list):
                                            entries_count = max(entries_count, len(value))
                            elif isinstance(data, list):
                                entries_count = len(data)
                    except (json.JSONDecodeError, IOError):
                        entries_count = 0

                    file_info = FileProcessingInfo(
                        filename=json_file.name,
                        filepath=str(json_file),
                        file_size_mb=file_size_mb,
                        entries_count=entries_count
                    )
                    files.append(file_info)

                except Exception as e:
                    logger.warning("Failed to process file", file=str(json_file), error=str(e))

            logger.info("Discovered RAG JSON files", count=len(files))

        except Exception as e:
            logger.error("Failed to discover files", error=str(e))

        return files

    async def ingest_file_to_ollama(self, file_info: FileProcessingInfo) -> bool:
        """Ingest a single RAG JSON file to Ollama"""
        try:
            file_info.status = FileStatus.IN_PROGRESS
            file_info.start_time = datetime.now()

            logger.info("Starting file ingestion", file=file_info.filename)

            # Read JSON file
            with open(file_info.filepath, 'r') as f:
                data = json.load(f)

            # Extract entries from various JSON structures
            entries = []
            if isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    entries = data['data']
                elif 'entries' in data and isinstance(data['entries'], list):
                    entries = data['entries']
                elif 'records' in data and isinstance(data['records'], list):
                    entries = data['records']
                else:
                    # Try to find the largest list in the data
                    for value in data.values():
                        if isinstance(value, list) and len(value) > len(entries):
                            entries = value
            elif isinstance(data, list):
                entries = data

            if not entries:
                logger.warning("No entries found in file", file=file_info.filename)
                file_info.status = FileStatus.SKIPPED
                return False

            # Process entries in batches
            ingested_count = 0
            failed_count = 0

            for i in range(0, len(entries), self.batch_size):
                if not self.is_running:
                    logger.info("Training stopped", file=file_info.filename)
                    file_info.status = FileStatus.FAILED
                    return False

                while self.is_paused:
                    await asyncio.sleep(1)

                batch = entries[i:i + self.batch_size]

                # Process batch
                for entry in batch:
                    try:
                        # Create prompt from entry
                        prompt = self._create_prompt_from_entry(entry, file_info.filename)

                        # Send to Ollama for ingestion
                        success = await self._send_to_ollama(prompt)

                        if success:
                            ingested_count += 1
                        else:
                            failed_count += 1

                    except Exception as e:
                        logger.warning("Entry processing failed", error=str(e))
                        failed_count += 1

                # Update progress
                file_info.ingested_items = ingested_count
                processed = ingested_count + failed_count
                file_info.success_rate = (ingested_count / processed * 100) if processed > 0 else 0.0

                # Small delay between batches
                await asyncio.sleep(0.5)

            # Mark as completed
            file_info.end_time = datetime.now()
            file_info.processing_time_seconds = (file_info.end_time - file_info.start_time).total_seconds()
            file_info.status = FileStatus.COMPLETED if ingested_count > 0 else FileStatus.FAILED

            logger.info(
                "File ingestion completed",
                file=file_info.filename,
                ingested=ingested_count,
                failed=failed_count,
                time_seconds=file_info.processing_time_seconds
            )

            return file_info.status == FileStatus.COMPLETED

        except Exception as e:
            logger.error("File ingestion failed", file=file_info.filename, error=str(e))
            file_info.status = FileStatus.FAILED
            file_info.error_message = str(e)
            return False

    def _create_prompt_from_entry(self, entry: Any, filename: str) -> str:
        """Create a training prompt from a data entry"""
        try:
            # Extract bank/symbol name from filename
            bank_name = filename.split('_')[0]

            # Build context from entry
            context_parts = [f"Symbol: {bank_name}"]

            if isinstance(entry, dict):
                # Extract date/timestamp
                for date_field in ['date', 'timestamp', 'time', 'datetime']:
                    if date_field in entry:
                        context_parts.append(f"Date: {entry[date_field]}")
                        break

                # Extract OHLC data
                ohlc_fields = ['open', 'high', 'low', 'close', 'volume']
                ohlc_data = {field: entry.get(field) for field in ohlc_fields if field in entry}
                if ohlc_data:
                    context_parts.append(f"OHLC: {ohlc_data}")

                # Extract technical indicators
                tech_indicators = {}
                for key, value in entry.items():
                    if any(indicator in key.lower() for indicator in ['rsi', 'macd', 'sma', 'ema', 'bb', 'atr']):
                        tech_indicators[key] = value

                if tech_indicators:
                    context_parts.append(f"Indicators: {tech_indicators}")

                # Extract any analysis or insights
                for insight_field in ['analysis', 'insight', 'summary', 'note', 'pattern']:
                    if insight_field in entry:
                        context_parts.append(f"{insight_field.title()}: {entry[insight_field]}")

            # Create structured prompt
            prompt = f"""You are analyzing historical trading data for {bank_name}.

Context:
{' | '.join(context_parts)}

Learn from this data point to improve your understanding of {bank_name}'s trading patterns and behavior.
Store this information for future market analysis and predictions.

Data: {json.dumps(entry, indent=2)}
"""

            return prompt

        except Exception as e:
            logger.warning("Failed to create prompt from entry", error=str(e))
            return f"Learn from this data: {json.dumps(entry)}"

    async def _send_to_ollama(self, prompt: str, retry_count: int = 0) -> bool:
        """Send prompt to Ollama for training/ingestion"""
        try:
            # Use Ollama CLI to send prompt
            process = await asyncio.create_subprocess_exec(
                "ollama", "run", self.model_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send prompt and get response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=30.0
            )

            if process.returncode == 0:
                return True
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.warning("Ollama command failed", error=error_msg, retry=retry_count)

                # Retry on failure
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                    return await self._send_to_ollama(prompt, retry_count + 1)

                return False

        except asyncio.TimeoutError:
            logger.warning("Ollama command timed out", retry=retry_count)
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                return await self._send_to_ollama(prompt, retry_count + 1)
            return False

        except Exception as e:
            logger.error("Failed to send to Ollama", error=str(e))
            return False

    def calculate_progress(self):
        """Calculate overall progress"""
        self.progress.total_files = len(self.files)
        self.progress.pending_files = sum(1 for f in self.files if f.status == FileStatus.PENDING)
        self.progress.in_progress_files = sum(1 for f in self.files if f.status == FileStatus.IN_PROGRESS)
        self.progress.completed_files = sum(1 for f in self.files if f.status == FileStatus.COMPLETED)
        self.progress.failed_files = sum(1 for f in self.files if f.status == FileStatus.FAILED)
        self.progress.skipped_files = sum(1 for f in self.files if f.status == FileStatus.SKIPPED)

        self.progress.total_entries_ingested = sum(f.ingested_items for f in self.files)
        self.progress.total_entries_processed = sum(f.entries_count for f in self.files if f.status != FileStatus.PENDING)

        # Calculate progress percentage
        if self.progress.total_files > 0:
            completed_and_processed = (
                self.progress.completed_files
                + self.progress.failed_files
                + self.progress.skipped_files
            )
            self.progress.overall_progress_percent = round(
                completed_and_processed / self.progress.total_files * 100,
                1
            )

        # Calculate elapsed time
        if self.progress.start_time:
            self.progress.elapsed_time_seconds = (datetime.now() - self.progress.start_time).total_seconds()

        # Estimate completion time
        if self.progress.completed_files > 0 and self.progress.elapsed_time_seconds > 0:
            avg_time_per_file = self.progress.elapsed_time_seconds / self.progress.completed_files
            remaining_files = self.progress.pending_files + self.progress.in_progress_files
            estimated_remaining_seconds = avg_time_per_file * remaining_files
            from datetime import timedelta
            self.progress.estimated_completion_time = datetime.now() + timedelta(seconds=estimated_remaining_seconds)

    async def start_training(self) -> Dict[str, Any]:
        """Start the RAG training process"""
        try:
            logger.info("Starting RAG training")

            # Discover files
            self.files = self.discover_files()
            if not self.files:
                return {
                    "success": False,
                    "error": "No RAG JSON files found",
                    "path": str(self.rag_json_dir)
                }

            # Initialize progress
            self.progress = TrainingProgress()
            self.progress.start_time = datetime.now()
            self.is_running = True

            # Process each file
            for file_info in self.files:
                if not self.is_running:
                    logger.info("Training stopped by user")
                    break

                # Wait if paused
                while self.is_paused:
                    await asyncio.sleep(1)

                # Process file
                await self.ingest_file_to_ollama(file_info)

                # Update progress
                self.calculate_progress()

            # Training completed
            self.is_running = False
            final_stats = self.get_final_statistics()

            logger.info("RAG training completed", **final_stats)

            return {
                "success": True,
                "statistics": final_stats,
                "files_processed": len([f for f in self.files if f.status == FileStatus.COMPLETED])
            }

        except Exception as e:
            logger.error("RAG training failed", error=str(e))
            self.is_running = False
            return {
                "success": False,
                "error": str(e)
            }

    def get_final_statistics(self) -> Dict[str, Any]:
        """Get final training statistics"""
        self.calculate_progress()

        total_time = self.progress.elapsed_time_seconds
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)

        return {
            "total_files": self.progress.total_files,
            "completed_files": self.progress.completed_files,
            "failed_files": self.progress.failed_files,
            "skipped_files": self.progress.skipped_files,
            "total_entries_ingested": self.progress.total_entries_ingested,
            "overall_progress_percent": self.progress.overall_progress_percent,
            "elapsed_time": f"{hours}h {minutes}m {seconds}s",
            "elapsed_time_seconds": total_time,
            "model_name": self.model_name
        }

    def pause_training(self):
        """Pause training"""
        self.is_paused = True
        logger.info("Training paused")

    def resume_training(self):
        """Resume training"""
        self.is_paused = False
        logger.info("Training resumed")

    def stop_training(self):
        """Stop training"""
        self.is_running = False
        self.is_paused = False
        logger.info("Training stopped")

    def get_current_status(self) -> Dict[str, Any]:
        """Get current training status"""
        self.calculate_progress()
        system_stats = self.system_monitor.get_system_stats()

        gpu_payload: Dict[str, Any] = {
            "available": bool(system_stats.gpu_name),
            "name": system_stats.gpu_name or "NVIDIA GPU not detected",
            "memory_percent": system_stats.gpu_memory_percent if system_stats.gpu_name else 0.0,
            "memory_used_mb": system_stats.gpu_memory_used_mb if system_stats.gpu_name else 0.0,
            "memory_total_mb": system_stats.gpu_memory_total_mb if system_stats.gpu_name else 0.0,
            "temperature": system_stats.gpu_temp,
            "fan_speed": system_stats.gpu_fan_speed,
            "utilization": system_stats.gpu_utilization if system_stats.gpu_name else 0.0,
            "note": None,
        }

        if not system_stats.gpu_name:
            gpu_payload["note"] = (
                "No NVIDIA GPU metrics detected. Verify drivers, CUDA, and nvidia-smi installation."
            )
        elif system_stats.gpu_utilization is None:
            gpu_payload["note"] = "Utilization data unavailable (try installing pynvml)."

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "progress": {
                "total_files": self.progress.total_files,
                "pending": self.progress.pending_files,
                "in_progress": self.progress.in_progress_files,
                "completed": self.progress.completed_files,
                "failed": self.progress.failed_files,
                "skipped": self.progress.skipped_files,
                "overall_percent": self.progress.overall_progress_percent,
                "elapsed_time_seconds": self.progress.elapsed_time_seconds,
                "entries_ingested": self.progress.total_entries_ingested
            },
            "system": {
                "cpu_percent": system_stats.cpu_percent,
                "cpu_temp": system_stats.cpu_temp,
                "memory_percent": system_stats.memory_percent,
                "memory_used_gb": system_stats.memory_used_gb,
                "memory_total_gb": system_stats.memory_total_gb,
                "disk_percent": system_stats.disk_percent,
                "disk_used_gb": system_stats.disk_used_gb,
                "disk_total_gb": system_stats.disk_total_gb,
                "gpu": gpu_payload
            },
            "files": [
                {
                    "filename": f.filename,
                    "status": f.status.value,
                    "size_mb": f.file_size_mb,
                    "entries": f.entries_count,
                    "ingested": f.ingested_items,
                    "success_rate": round(f.success_rate, 1),
                    "processing_time": round(f.processing_time_seconds, 1)
                }
                for f in self.files
            ]
        }


# CLI test function
async def test_training():
    """Test RAG training orchestrator"""

    rag_dir = "/home/pranay/Music/niraj/historical/rag_json"
    orchestrator = RAGTrainingOrchestrator(rag_dir)

    print("🚀 Starting RAG Training Test")
    print(f"📁 RAG Directory: {rag_dir}")
    print(f"🤖 Model: {orchestrator.model_name}")
    print("-" * 60)

    # Start training
    result = await orchestrator.start_training()

    print("\n" + "=" * 60)
    print("✅ Training Completed!")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(test_training())
