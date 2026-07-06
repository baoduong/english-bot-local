# Install BE as Windows service (auto-start on boot) using NSSM
# Run as Administrator

if (!(Get-Command nssm -ErrorAction SilentlyContinue)) {
    choco install -y nssm
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = "$RepoRoot\venv\Scripts\python.exe"
$UvicornArgs = "-m uvicorn api.main:app --host 0.0.0.0 --port 8080"

nssm install EnglishBotBE $Python $UvicornArgs
nssm set EnglishBotBE AppDirectory $RepoRoot
nssm set EnglishBotBE Description "English Bot FastAPI Backend"
nssm set EnglishBotBE Start SERVICE_AUTO_START
nssm set EnglishBotBE AppStdout "$RepoRoot\logs\uvicorn.log"
nssm set EnglishBotBE AppStderr "$RepoRoot\logs\uvicorn.err.log"

New-Item -ItemType Directory -Force "$RepoRoot\logs" | Out-Null

nssm start EnglishBotBE

Write-Host "Service installed and started. Manage with:"
Write-Host "  nssm start/stop/restart/remove EnglishBotBE"
