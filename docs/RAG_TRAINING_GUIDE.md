# RAG Training Guide - Gemma3 Model with Bank Stock Data

## Overview

The NIRAJ Trading System now includes a comprehensive RAG (Retrieval-Augmented Generation) training feature that enables the Ollama Gemma3 model to learn from historical bank stock trading data. This feature provides real-time monitoring, progress tracking, and system resource visualization during the training process.

## 🎯 Features

### Core Functionality
- **Batch Processing**: Processes multiple RAG JSON files containing bank stock data
- **Real-time Dashboard**: Live updates every 2 seconds with comprehensive metrics
- **System Monitoring**: Tracks CPU, GPU, Memory, Disk, Temperature, and Fan Speed
- **Progress Tracking**: Shows completed, in-progress, pending, failed, and skipped files
- **Error Handling**: Automatic retry mechanism with configurable retry count
- **Graceful Interruption**: Allows stopping training at any time with Ctrl+C

### Dashboard Components
1. **Progress Section**
   - Total files count
   - Completed, In Progress, Pending, Failed, Skipped counts
   - Overall progress percentage with visual progress bar
   - Total entries ingested
   - Elapsed time display (HH:MM:SS)

2. **System Resources**
   - CPU usage percentage and temperature
   - Memory usage (percentage and GB)
   - Disk usage (percentage and GB)

3. **GPU Statistics** (NVIDIA GPUs)
   - GPU name and model
   - GPU memory usage (percentage and MB)
   - GPU temperature with color-coded alerts
   - GPU fan speed percentage
   - GPU utilization percentage

4. **File Status**
   - Last 10 files being processed
   - Status indicators (⏸️ Pending, ⏳ In Progress, ✅ Completed, ❌ Failed, ⏭️ Skipped)
   - Success rate per file
   - Processing time per file

## 📋 Prerequisites

### System Requirements
1. **NVIDIA GPU** (Recommended but not required)
   - NVIDIA drivers installed
   - `nvidia-smi` available
   - 4GB+ VRAM for Gemma3 4B model

2. **Ollama**
   - Version 0.11.8 or higher
   - Installed and accessible via CLI
   - `ollama` command in PATH

3. **Python Dependencies**
   - `psutil` - System monitoring
   - `structlog` - Structured logging
   - `asyncio` - Async operations

### Verification Commands
```bash
# Check NVIDIA GPU
nvidia-smi --version

# Check Ollama
ollama --version

# List Ollama models
ollama list
```

## 🚀 Getting Started

### Step 1: Prepare RAG JSON Files

Ensure your bank stock data is converted to RAG JSON format and located in:
```
/home/pranay/Music/niraj/historical/rag_json/
```

Expected file format: `BANKNAME_timeframe_rag.json`

Examples:
- `HDFCBANK_daily_rag.json`
- `ICICIBANK_15min_rag.json`
- `SBI_daily_rag.json`

### Step 2: Launch NIRAJ Menu

```bash
cd /home/pranay/Music/niraj
python niraj.py
```

### Step 3: Select RAG Training

From the main menu, select option **19**:
```
19. 🤖 RAG Training (Gemma3)
```

### Step 4: System Check

The system will automatically verify:
- ✅ GPU availability and specifications
- ✅ Ollama installation
- ✅ Gemma3 model availability
- ✅ RAG JSON files count and location

If Gemma3 model is not found, you'll be prompted to download it:
```
Pull gemma3:4b-it-q4_K_M model? (yes/no):
```

### Step 5: Review Training Information

Before starting, review the displayed information:
- Model name: `gemma3:4b-it-q4_K_M`
- Number of files to process
- RAG JSON directory location
- Estimated training time

### Step 6: Confirm and Start

Type `yes` or `y` to start training:
```
▶️  Start RAG training? (yes/no): yes
```

## 📊 Understanding the Dashboard

### Progress Bar
```
[████████████████████████████████████░░░░░░░░░░] 75.0%
```
- Filled blocks (█): Completed percentage
- Empty blocks (░): Remaining percentage

### Status Indicators

| Icon | Status | Meaning |
|------|--------|---------|
| ⏸️ | Pending | File waiting to be processed |
| ⏳ | In Progress | Currently processing file |
| ✅ | Completed | Successfully processed |
| ❌ | Failed | Processing failed |
| ⏭️ | Skipped | File skipped (no data) |

### Temperature Color Coding

GPU temperature is color-coded for safety:
- 🟢 **Green** (< 70°C): Safe operating temperature
- 🟡 **Yellow** (70-80°C): Warm, monitor closely
- 🔴 **Red** (> 80°C): High temperature, consider cooling

## ⚙️ Configuration

### Batch Size
Default: 10 entries per batch
Location: `rag_training_orchestrator.py`
```python
self.batch_size = 10  # Adjust based on GPU memory
```

### Retry Mechanism
Default: 3 retries with 5-second delay
```python
self.max_retries = 3
self.retry_delay = 5  # seconds
```

### Dashboard Update Interval
Default: 2 seconds
```python
await asyncio.sleep(2)  # Update frequency
```

## 🔧 Troubleshooting

### Issue: "Ollama not found"
**Solution:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Or download from https://ollama.ai/download
```

### Issue: "Gemma3 model not found"
**Solution:**
```bash
# Pull the model manually
ollama pull gemma3:4b-it-q4_K_M

# Verify installation
ollama list | grep gemma3
```

### Issue: "No NVIDIA GPU detected"
**Impact:** Training will use CPU (slower but functional)

**To enable GPU:**
1. Install NVIDIA drivers for your GPU
2. Verify with `nvidia-smi`
3. Restart training

### Issue: "GPU memory error"
**Solution:**
1. Close other GPU-intensive applications
2. Reduce batch_size in orchestrator
3. Use a smaller model variant

### Issue: "Training is very slow"
**Optimization tips:**
1. Ensure GPU is being utilized (check GPU utilization in dashboard)
2. Increase batch_size if GPU memory allows
3. Close unnecessary applications
4. Use SSD for RAG JSON files location

### Issue: "File processing failed"
**Common causes:**
1. Invalid JSON format - Check file syntax
2. Missing data fields - Verify JSON structure
3. File permissions - Ensure read access
4. Corrupted file - Re-download or regenerate

## 📈 Performance Optimization

### For CPU Training
- Close background applications
- Reduce batch_size to 5-8
- Process fewer files at once
- Use smaller model variants

### For GPU Training
- Monitor GPU temperature (keep below 80°C)
- Increase batch_size to 15-20 if 6GB+ VRAM
- Enable GPU fan control (Option 17 in menu)
- Ensure proper ventilation

### For Large Datasets
- Process files in multiple sessions
- Monitor disk space
- Use RAG JSON files on SSD
- Schedule training during low-usage periods

## 📝 Training Data Format

### Expected JSON Structure
```json
{
  "data": [
    {
      "date": "2023-01-01",
      "open": 1500.50,
      "high": 1520.75,
      "low": 1495.25,
      "close": 1515.00,
      "volume": 1000000,
      "rsi": 65.5,
      "macd": 0.15,
      "sma_20": 1510.00,
      "analysis": "Bullish momentum with increasing volume"
    }
  ]
}
```

### Alternative Structures Supported
- `entries` array
- `records` array
- Direct array format
- Nested data objects

## 🎓 Training Process

### What Happens During Training

1. **File Discovery**
   - Scans RAG JSON directory
   - Counts entries in each file
   - Calculates file sizes

2. **Data Preparation**
   - Extracts OHLC data
   - Identifies technical indicators
   - Formats contextual information
   - Creates training prompts

3. **Ollama Ingestion**
   - Sends prompts to Gemma3 model
   - Processes in configurable batches
   - Implements retry mechanism
   - Tracks success/failure rates

4. **Knowledge Storage**
   - Model learns patterns
   - Stores trading insights
   - Builds contextual understanding
   - Enables future predictions

## 📊 Post-Training

### Verify Training Success
After training completes, the model should have learned:
- Bank stock trading patterns
- Technical indicator relationships
- Market behavior trends
- Historical price movements

### Test the Trained Model
```bash
# Interactive test
ollama run gemma3:4b-it-q4_K_M

# Test query example
"Analyze the trading pattern for HDFCBANK based on historical data"
```

### Training Statistics
Final statistics include:
- Total files processed
- Success rate per file
- Total entries ingested
- Training duration
- System resource usage

## 🛡️ Safety Features

### Graceful Shutdown
- Press `Ctrl+C` at any time to stop
- Training saves progress up to current file
- No data corruption risk
- Clean resource cleanup

### Error Recovery
- Automatic retry on transient failures
- Continues with next file on persistent errors
- Detailed error logging
- Final failure report

### Resource Protection
- Monitors system temperature
- Alerts on high resource usage
- Respects GPU memory limits
- Prevents system overload

## 📚 Related Documentation

- `RAG_CONVERSION_SUMMARY.md` - RAG JSON conversion guide
- `BANK_STOCKS_IMPLEMENTATION_SUMMARY.md` - Bank stock data overview
- `HISTORICAL_DATA_DOWNLOAD_REPORT.md` - Data download guide
- `backend/src/ai/rag_processor.py` - RAG processor implementation

## 🔍 Technical Details

### Architecture
```
niraj.py (Menu Interface)
    ↓
handle_rag_training() (Option 19)
    ↓
rag_training_orchestrator.py (Orchestrator)
    ↓
    ├── SystemMonitor (Resource tracking)
    ├── FileProcessingInfo (File status)
    ├── TrainingProgress (Overall progress)
    └── Ollama CLI (Model training)
```

### File Locations
- Main script: `niraj.py`
- Orchestrator: `rag_training_orchestrator.py`
- RAG JSON: `historical/rag_json/`
- RAG Processor: `backend/src/ai/rag_processor.py`

### Dependencies
```python
# Core
import asyncio
import json
import subprocess

# System monitoring
import psutil
import structlog

# Type hints
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
```

## 💡 Tips & Best Practices

1. **Before Training**
   - Verify GPU drivers are up to date
   - Close unnecessary applications
   - Ensure adequate disk space (5GB+ free)
   - Check RAG JSON files are valid

2. **During Training**
   - Monitor GPU temperature regularly
   - Don't interrupt abruptly (use Ctrl+C)
   - Watch for memory warnings
   - Note any failing files for review

3. **After Training**
   - Test model with sample queries
   - Review training statistics
   - Check failed files if any
   - Consider retraining failed files

4. **Regular Maintenance**
   - Update RAG JSON files monthly
   - Retrain model quarterly
   - Monitor model performance
   - Clean up old training logs

## ❓ FAQ

**Q: How long does training take?**
A: 10-30 minutes for ~40 files, depending on file size and hardware.

**Q: Can I train on CPU only?**
A: Yes, but it will be significantly slower (2-3x longer).

**Q: What happens if training is interrupted?**
A: Progress is lost, but no data corruption. Simply restart training.

**Q: Can I train custom data?**
A: Yes, format your data as RAG JSON and place in the rag_json directory.

**Q: How much GPU memory is needed?**
A: Minimum 4GB for gemma3:4b model, 6GB+ recommended for better performance.

**Q: Can I run other tasks during training?**
A: Yes, but GPU-intensive tasks may slow training or cause errors.

**Q: How do I verify the model learned correctly?**
A: Test with queries about banks in your training data using `ollama run gemma3`.

**Q: Can I train multiple models?**
A: Yes, but change model_name in orchestrator to target different models.

## 🎉 Success Indicators

Training is successful when you see:
- ✅ High completion rate (>90%)
- ✅ Low failure rate (<5%)
- ✅ Most entries ingested
- ✅ Stable GPU temperature
- ✅ No memory errors
- ✅ Model responds with relevant trading insights

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review error logs in terminal
3. Verify system requirements
4. Test with smaller dataset first
5. Report persistent issues with logs

---

**Version:** 1.0
**Last Updated:** October 5, 2025
**Compatible with:** NIRAJ Trading System v2.0+
