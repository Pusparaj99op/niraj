# Ubuntu NVIDIA GPU + Ollama Setup Guide

This guide walks through installing the NVIDIA driver stack, CUDA tooling, GPU monitoring utilities, and the Ollama runtime on Ubuntu so the Gemma3 model trains on the GPU.

> **Target OS:** Ubuntu 22.04 LTS (Jammy) or later
> **Hardware:** NVIDIA GeForce / RTX GPU
> **Privileges:** sudo

---

## 1. Prepare the system

```bash
# Update package index and upgrade
sudo apt update
sudo apt upgrade -y

# Install base tooling
sudo apt install -y build-essential dkms linux-headers-$(uname -r) curl wget git
```

If you previously installed community or Nouveau drivers, purge them:

```bash
sudo apt purge 'nvidia-*' 'cuda-*' -y
sudo apt autoremove -y
sudo reboot
```

---

## 2. Install proprietary NVIDIA drivers

Ubuntu ships the `ubuntu-drivers` helper which selects the recommended driver for your GPU.

```bash
sudo ubuntu-drivers devices            # Optional: list recommended versions
sudo ubuntu-drivers autoinstall        # Installs the tested proprietary driver
sudo reboot                            # Required after driver installation
```

After reboot, verify the driver and GPU visibility:

```bash
nvidia-smi
```

You should see a table with GPU name, driver version, and usage. If the command is missing, confirm `nvidia-utils-XXX` is installed or rerun `ubuntu-drivers autoinstall`.

---

## 3. Install CUDA toolkit (optional but recommended)

CUDA libraries provide additional GPU tooling and are required for some packages.

```bash
sudo apt install -y nvidia-cuda-toolkit
nvcc --version                          # Confirms CUDA compiler availability
```

Omitting CUDA is possible if you only need `nvidia-smi`, but CUDA ensures development headers are available for packages such as `pynvml` and deep-learning frameworks.

---

## 4. Install GPU monitoring libraries for Python

`pynvml` exposes detailed GPU stats (temperature, fan speed, utilization) to the RAG training orchestrator.

```bash
# Inside the NIRAJ project directory
cd /home/pranay/Music/niraj
poetry add pynvml                       # Already added to pyproject; installs to the env
```

If you are not using Poetry, install system-wide:

```bash
pip install --upgrade pynvml
```

---

## 5. Install Ollama with GPU support

Ollama provides optimized Gemma3 builds. Install via the official script:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

Enable GPU acceleration for Ollama (newer versions detect automatically, but set the variable explicitly to be safe):

```bash
sudo systemctl stop ollama
sudo systemctl edit ollama.service
```

Add/ensure the following lines inside the systemd override file:

```
[Service]
Environment=OLLAMA_USE_GPU=1
```

Reload and start Ollama:

```bash
sudo systemctl daemon-reload
sudo systemctl start ollama
```

Verify Ollama sees the GPU:

```bash
ollama run llama3 "Say hello from the GPU"
ollama list
```

---

## 6. Pull the Gemma3 model

```bash
ollama pull gemma3:4b-it-q4_K_M
```

Check disk space (model ~3.3 GB) and confirm it appears in `ollama list`.

---

## 7. Post-install verification

Run the following to confirm every layer is operational:

```bash
# Driver + GPU visibility
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

# CUDA compiler (optional)
nvcc --version

# Python NVML bindings
python - <<'PY'
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetName
nvmlInit()
handle = nvmlDeviceGetHandleByIndex(0)
print("Detected GPU:", nvmlDeviceGetName(handle))
PY

# Ollama runtime
ollama run gemma3:4b-it-q4_K_M "How many GPUs are available on this host?"
```

If any command fails, revisit the earlier sections or consult the troubleshooting tips below.

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `nvidia-smi`: "command not found" | Driver utilities not installed | Rerun `sudo ubuntu-drivers autoinstall`; ensure PATH includes `/usr/bin`. |
| `nvidia-smi` shows `No devices were found` | Secure Boot blocking driver or reboot pending | Disable Secure Boot in BIOS, rerun driver install, then reboot. |
| Fan speed returns `N/A` | Many laptops lock fan telemetry | Use external cooling; fan metrics may remain unavailable. |
| `pynvml` import fails | Package not installed in environment | Run `poetry install` or `pip install pynvml`. |
| Ollama errors about GPU support | Old version or environment variable missing | Update Ollama (`ollama update`), set `OLLAMA_USE_GPU=1`, restart service. |
| Training dashboard still shows no GPU | Run `nvidia-smi` manually; if it fails, drivers not loaded. If it works, ensure Python env uses the same interpreter (`poetry run python`). |

---

## 9. Quick verification checklist

- [ ] `nvidia-smi` shows your GPU (e.g., **RTX 3050 Laptop GPU**)
- [ ] `nvcc --version` prints CUDA compiler info (optional)
- [ ] `python -c "import pynvml"` runs without errors
- [ ] `ollama list` includes `gemma3:4b-it-q4_K_M`
- [ ] NIRAJ RAG dashboard displays GPU memory, utilization, and temperature

With the drivers and tooling in place, rerun **Menu option 19** in `niraj.py`. The dashboard should now highlight GPU metrics in real time while the Gemma3 model ingests your RAG JSON files.
