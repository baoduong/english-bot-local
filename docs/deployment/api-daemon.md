# API Daemon — Deployment Guide

FastAPI gateway running as a **launchd user agent** on macOS.  
The daemon starts automatically at login and restarts automatically if the process exits.

---

## Prerequisites

| Requirement | Minimum version | Check |
|---|---|---|
| macOS | 12 Monterey+ | `sw_vers` |
| Python | 3.9+ | `python3 --version` |
| virtualenv at `venv/` | — | `ls venv/bin/uvicorn` |
| Ollama | latest | `ollama --version` |
| ffmpeg | any | `ffmpeg -version` |
| Project root on disk | `/Volumes/BAODUONG/english-bot-local` | `ls` |

Ollama must have the model available:

```bash
ollama pull gemma4:31b-cloud
# verify
ollama list | grep gemma4
```

---

## Project structure after setup

```
english-bot-local/
├── api/
│   ├── config.py          ← Settings + logging helpers (new)
│   └── main.py            ← FastAPI app entry point
├── logs/
│   ├── api.log            ← structured JSON log (rotating 10 MB × 5)
│   ├── api.stdout.log     ← uvicorn stdout captured by launchd
│   └── api.stderr.log     ← uvicorn stderr captured by launchd
├── scripts/
│   └── launchd/
│       └── com.englishbot.api.plist   ← launchd job definition
├── docs/
│   └── deployment/
│       └── api-daemon.md  ← this file
├── .env                   ← secrets (not tracked by git)
└── venv/                  ← Python virtual environment
```

---

## Environment variables

The plist sets the following variables directly.  
Secrets that already exist in `.env` are loaded by `python-dotenv` at runtime — you do **not** need to duplicate them in the plist.

| Variable | Default in plist | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Listening port |
| `LOG_PATH` | `…/logs/api.log` | JSON rotating log file |
| `DB_PATH` | `…/english_learner.db` | SQLite database path |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | Model name for Ollama |
| `PYTHONUNBUFFERED` | `1` | Flush stdout/stderr immediately |
| `PYTHONPATH` | project root | Allows `from api.main import …` |

To override a value without editing the plist, export the variable before loading:

```bash
# example: use a different port
launchctl setenv API_PORT 8080
# then reload the daemon (see below)
```

---

## Install steps

### 1. Ensure the logs directory exists

```bash
mkdir -p /Volumes/BAODUONG/english-bot-local/logs
```

### 2. Populate `.env` with required secrets

```bash
# /Volumes/BAODUONG/english-bot-local/.env
USE_AZURE_SPEECH=false
AZURE_SPEECH_KEY=<your_key>
AZURE_SPEECH_REGION=southeastasia
```

### 3. Install Python dependencies (if not already)

```bash
cd /Volumes/BAODUONG/english-bot-local
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 4. Verify the plist is valid

```bash
plutil -lint scripts/launchd/com.englishbot.api.plist
# Expected: scripts/launchd/com.englishbot.api.plist: OK
```

### 5. Copy the plist to the launchd agents directory

```bash
cp scripts/launchd/com.englishbot.api.plist \
   ~/Library/LaunchAgents/com.englishbot.api.plist
```

> **Why `~/Library/LaunchAgents/`?**  
> LaunchAgents run as the current user (not root), so they can access the
> external volume, the user keychain, and the display session — appropriate
> for a trusted-LAN service on a personal Mac.

---

## Start / stop / restart

### Load and start (first time, or after plist edit)

```bash
launchctl load ~/Library/LaunchAgents/com.englishbot.api.plist
```

Because `RunAtLoad = true`, the daemon starts immediately after loading.

### Stop and unload

```bash
launchctl unload ~/Library/LaunchAgents/com.englishbot.api.plist
```

### Restart (apply plist changes)

```bash
launchctl unload ~/Library/LaunchAgents/com.englishbot.api.plist
launchctl load   ~/Library/LaunchAgents/com.englishbot.api.plist
```

### Reload without full unload (macOS 13+)

```bash
launchctl kickstart -k gui/$(id -u)/com.englishbot.api
```

---

## Check if the daemon is running

```bash
# List all jobs matching the label
launchctl list | grep com.englishbot.api

# Detailed job state (PID, exit code, last error)
launchctl print gui/$(id -u)/com.englishbot.api
```

**Reading the output of `launchctl list`:**

| Column | Meaning |
|---|---|
| PID (non-zero) | process is running |
| `0` in exit column | last run exited cleanly |
| non-zero exit | last run crashed; check logs |

### Quick HTTP health check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected response:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## Log file locations

| File | Content | Rotation |
|---|---|---|
| `logs/api.log` | Structured JSON application logs | 10 MB × 5 backups (Python `RotatingFileHandler`) |
| `logs/api.stdout.log` | uvicorn access log + startup messages | Not rotated — use `newsyslog` if needed |
| `logs/api.stderr.log` | uvicorn errors + Python tracebacks | Not rotated — use `newsyslog` if needed |

### Follow live application logs

```bash
# JSON logs (application events)
tail -f /Volumes/BAODUONG/english-bot-local/logs/api.log

# Pretty-print JSON lines
tail -f /Volumes/BAODUONG/english-bot-local/logs/api.log \
  | python3 -c "import sys,json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]"

# uvicorn access / error stream
tail -f /Volumes/BAODUONG/english-bot-local/logs/api.stdout.log
tail -f /Volumes/BAODUONG/english-bot-local/logs/api.stderr.log
```

### Rotate stdout/stderr logs via newsyslog (optional)

Create `/etc/newsyslog.d/com.englishbot.api.conf`:

```
/Volumes/BAODUONG/english-bot-local/logs/api.stdout.log  644  5  10240  *  J
/Volumes/BAODUONG/english-bot-local/logs/api.stderr.log  644  5  10240  *  J
```

---

## Troubleshooting

### Daemon doesn't start / exits immediately

1. Check the exit code:
   ```bash
   launchctl list | grep com.englishbot.api
   ```
2. Read the stderr log for the traceback:
   ```bash
   cat logs/api.stderr.log
   ```
3. Common causes:
   - `venv/bin/uvicorn` not found → re-create venv and install deps
   - `PYTHONPATH` not including project root → verify plist `WorkingDirectory`
   - Port 8000 already in use → `lsof -i :8000`; change `API_PORT`

### `ModuleNotFoundError` on startup

The plist sets `PYTHONPATH` to the project root. If you move the project, update **both** `WorkingDirectory` and `PYTHONPATH` in the plist, then reload.

```bash
# After editing the plist in scripts/launchd/, re-copy and reload:
cp scripts/launchd/com.englishbot.api.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.englishbot.api.plist
launchctl load   ~/Library/LaunchAgents/com.englishbot.api.plist
```

### Ollama 503 errors in the log

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags
# Start if needed
ollama serve &
```

### Process restarts in a tight loop (ThrottleInterval)

The plist uses `ThrottleInterval = 10` seconds to prevent a crash loop from
hammering the CPU. If the process crashes repeatedly, launchd will keep
retrying every 10 s. Fix the underlying error, then:

```bash
launchctl unload ~/Library/LaunchAgents/com.englishbot.api.plist
# fix the issue
launchctl load   ~/Library/LaunchAgents/com.englishbot.api.plist
```

### macOS Gatekeeper / volume permission

Because the project lives on an external volume (`/Volumes/BAODUONG/…`),
make sure the volume is mounted **before** the user agent tries to start.
Add a `WatchPaths` or `PathState` entry to the plist if the volume is not
always mounted at login:

```xml
<key>WatchPaths</key>
<array>
  <string>/Volumes/BAODUONG/english-bot-local</string>
</array>
```

---

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.englishbot.api.plist
rm ~/Library/LaunchAgents/com.englishbot.api.plist
```

The project files and logs are untouched; only the daemon registration is removed.
