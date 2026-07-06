# Windows Setup Script for English Bot Backend
# Run as Administrator in PowerShell

$ErrorActionPreference = "Stop"
Write-Host "=== English Bot BE — Windows Setup ===" -ForegroundColor Cyan

# 1. Check/install Chocolatey
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
    $env:PATH = "$env:PATH;$env:ALLUSERSPROFILE\chocolatey\bin"
}

# 2. Install system packages via choco
Write-Host "Installing Python 3.11 + ffmpeg + git..." -ForegroundColor Yellow
choco install -y python311 ffmpeg git

# 3. Install espeak-ng (manual — no reliable choco package)
Write-Host "Please install eSpeak NG manually:" -ForegroundColor Yellow
Write-Host "  1. Download: https://github.com/espeak-ng/espeak-ng/releases/latest"
Write-Host "  2. Run the .msi installer"
Write-Host "  3. Verify: 'C:\Program Files\eSpeak NG\espeak-ng.exe --version'"
Read-Host "Press Enter after installing espeak-ng"

# 4. Verify espeak-ng
$espeakPath = "C:\Program Files\eSpeak NG"
if (!(Test-Path "$espeakPath\espeak-ng.exe")) {
    Write-Host "ERROR: eSpeak NG not found at $espeakPath" -ForegroundColor Red
    exit 1
}

# 5. Add espeak-ng to PATH (permanent)
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($currentPath -notlike "*$espeakPath*") {
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$espeakPath", "Machine")
    Write-Host "Added $espeakPath to system PATH" -ForegroundColor Green
}

# 6. Install Ollama (native Windows)
Write-Host "Please install Ollama:" -ForegroundColor Yellow
Write-Host "  1. Download: https://ollama.com/download/windows"
Write-Host "  2. Run OllamaSetup.exe"
Write-Host "  3. Verify Ollama is running: 'ollama list'"
Read-Host "Press Enter after installing Ollama"

# 7. Pull Ollama model
Write-Host "Pulling gemma model (may take 10-30 min, ~18GB)..." -ForegroundColor Yellow
ollama pull gemma4:31b-cloud

# 8. Python venv + dependencies
Write-Host "Setting up Python venv..." -ForegroundColor Yellow
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt

# 9. Firewall rule for port 8000
Write-Host "Adding Windows Firewall rule for port 8000..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "EnglishBot BE" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue

# 10. Optional: Bonjour Print Services for iOS auto-discovery
Write-Host "For iOS Bonjour auto-discovery, install Apple Bonjour Print Services:" -ForegroundColor Yellow
Write-Host "  https://support.apple.com/kb/DL999"
Write-Host "  (Optional — iPhone can also use manual URL entry in Settings)"

# 11. Verify installation
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
Write-Host "Python:  $(.\venv\Scripts\python.exe --version)"
Write-Host "ffmpeg:  $(ffmpeg -version 2>&1 | Select-Object -First 1)"
Write-Host "espeak:  $(& "$espeakPath\espeak-ng.exe" --version 2>&1 | Select-Object -First 1)"
Write-Host "Ollama:  $(ollama --version)"

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host "To start backend, run: .\scripts\windows-run.ps1"
