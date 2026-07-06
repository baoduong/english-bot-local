# Windows Deployment Guide

Deploy the English Bot FastAPI backend on native Windows 10/11 (no WSL required).

## Prerequisites

- Windows 10 (1903+) or Windows 11
- Administrator access
- ~30 GB free disk space (Ollama model ~18 GB + Python packages ~5 GB)
- Wi-Fi connection on the same network as your iPhone

---

## Automated Setup

Run the setup script once as Administrator:

```powershell
# Open PowerShell as Administrator, then:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
cd C:\path\to\english-bot-local
.\scripts\windows-setup.ps1
```

The script installs: Chocolatey → Python 3.11 → ffmpeg → git → espeak-ng (manual prompt) → Ollama (manual prompt) → Python venv + pip packages → Windows Firewall rule.

---

## Manual Setup Steps

Use these if the automated script fails at any step.

### 1. Install Chocolatey

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
```

### 2. Install Python 3.11, ffmpeg, git

```powershell
choco install -y python311 ffmpeg git
```

Restart PowerShell after this step so `py` and `ffmpeg` are on PATH.

### 3. Install eSpeak NG

1. Download the latest `.msi` from <https://github.com/espeak-ng/espeak-ng/releases/latest>
2. Run the installer (default path: `C:\Program Files\eSpeak NG`)
3. Verify:
   ```powershell
   & "C:\Program Files\eSpeak NG\espeak-ng.exe" --version
   ```
4. Add to system PATH permanently:
   ```powershell
   $p = [Environment]::GetEnvironmentVariable("PATH","Machine")
   [Environment]::SetEnvironmentVariable("PATH","$p;C:\Program Files\eSpeak NG","Machine")
   ```
   Restart PowerShell after this.

### 4. Install Ollama

1. Download from <https://ollama.com/download/windows>
2. Run `OllamaSetup.exe` — it installs as a background service
3. Verify it's running:
   ```powershell
   ollama list
   ```

### 5. Pull the Ollama model

```powershell
ollama pull gemma4:31b-cloud
```

This downloads ~18 GB. Allow 10–30 minutes depending on connection speed.

### 6. Create Python venv and install dependencies

```powershell
cd C:\path\to\english-bot-local
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 7. Open Windows Firewall for port 8000

```powershell
New-NetFirewallRule -DisplayName "EnglishBot BE" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## Running the Backend

```powershell
.\scripts\windows-run.ps1
```

The script:
1. Detects your local Wi-Fi IP and prints the iPhone URL
2. Verifies Ollama is running (exits with error if not)
3. Starts uvicorn on `0.0.0.0:8000`

Wait for the log line `Whisper model loaded` before opening the iOS app.

---

## Auto-Start as Windows Service

To have the backend start automatically on boot (no login required):

```powershell
# Run as Administrator
.\scripts\windows-install-service.ps1
```

This uses [NSSM](https://nssm.cc) to register `EnglishBotBE` as a Windows service.

Manage the service:

```powershell
nssm start EnglishBotBE
nssm stop EnglishBotBE
nssm restart EnglishBotBE
nssm remove EnglishBotBE confirm
```

Logs are written to `logs\uvicorn.log` and `logs\uvicorn.err.log` in the repo root.

---

## iPhone Connection

### Option A: Bonjour auto-discovery (recommended)

1. Install [Apple Bonjour Print Services](https://support.apple.com/kb/DL999) on Windows
2. The iPhone app will discover the backend automatically on the same Wi-Fi network

### Option B: Manual IP entry

1. Find your Windows IP:
   ```powershell
   (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi").IPAddress
   ```
2. In the iOS app → Settings → enter `http://<your-ip>:8000`

Both options require the iPhone and Windows PC to be on the same Wi-Fi network.

---

## Troubleshooting

### "espeak-ng not found" at model load

The phoneme recognizer needs `espeak-ng.exe` on PATH. Check:

```powershell
where.exe espeak-ng
```

If not found, re-run step 3 above and restart PowerShell. The backend's `engines/phoneme_recognizer.py` also checks `C:\Program Files\eSpeak NG` automatically at import time.

### "Ollama connection refused"

Ollama must be running before starting the backend. Open the Start Menu and launch **Ollama**, or:

```powershell
ollama serve
```

Verify with `ollama list` — it should return the model list without error.

### "iPhone can't connect"

1. Confirm both devices are on the same Wi-Fi network
2. Check the firewall rule exists:
   ```powershell
   Get-NetFirewallRule -DisplayName "EnglishBot BE"
   ```
3. Try pinging the Windows IP from iPhone (Settings → Wi-Fi → tap network → note IP, then test from a browser: `http://<windows-ip>:8000/health`)
4. Temporarily disable Windows Defender Firewall to isolate the issue

### Slow inference (~2–5 s per audio scoring)

Expected on CPU-only mode. Windows does not support Apple MPS. If you have an NVIDIA GPU:

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Replace `cu121` with your CUDA version (`nvidia-smi` shows it). After reinstalling torch, Whisper and the phoneme model will use CUDA automatically.

### PyTorch device

On Windows without NVIDIA GPU, PyTorch defaults to CPU. This is expected and fully supported — no code changes needed. Inference is slower (~2–5 s) but correct.

### Port 8000 already in use

```powershell
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```
