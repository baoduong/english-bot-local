# Start English Bot Backend on Windows

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Wi-Fi" -ErrorAction SilentlyContinue).IPAddress
if (-not $LocalIP) {
    $LocalIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1).IPAddress
}

Write-Host "=== Starting English Bot BE ===" -ForegroundColor Cyan
Write-Host "Local IP:  $LocalIP" -ForegroundColor Green
Write-Host "iPhone URL: http://${LocalIP}:8000" -ForegroundColor Green
Write-Host "Health:    http://localhost:8000/health"
Write-Host ""

try {
    Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null
    Write-Host "Ollama running" -ForegroundColor Green
} catch {
    Write-Host "Ollama not running. Start Ollama from Start Menu." -ForegroundColor Red
    exit 1
}

.\venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
