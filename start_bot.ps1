# ============================================================
# 🌙 Moon Dev Bot — Windows Launch Script
# ============================================================
# Usage:
#   Right-click → "Run with PowerShell"
#   OR from terminal: .\start_bot.ps1
#   OR with mode:     .\start_bot.ps1 -Mode rbi
#
# Modes:
#   main      → Full orchestrator (default)
#   rbi       → RBI agent only (backtest pipeline)
#   risk      → Risk agent only
#   signal    → Signal fusion agent only
#   dashboard → Backtest dashboard (http://localhost:8001)
# ============================================================

param(
    [string]$Mode = "main",
    [switch]$Background = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$SrcDir   = Join-Path $RepoRoot "src"

# ─── Colour helpers ───────────────────────────────────────
function Info  ($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok    ($msg) { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Warn  ($msg) { Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Err   ($msg) { Write-Host "  ❌ $msg" -ForegroundColor Red }
function Banner($msg) { Write-Host "`n🌙  $msg`n" -ForegroundColor White -BackgroundColor DarkBlue }

Banner "Moon Dev AI Trading Bot — Windows Launcher"
Info "Mode: $Mode"
Info "Repo: $RepoRoot"

# ─── Check Python ─────────────────────────────────────────
try {
    $pyver = python --version 2>&1
    Ok "Python: $pyver"
} catch {
    Err "Python not found. Install from https://python.org"
    exit 1
}

# ─── Check .env exists ────────────────────────────────────
$envFile = Join-Path $SrcDir ".env"
if (-not (Test-Path $envFile)) {
    Warn ".env not found at $envFile"
    Warn "Copy src/.env_example to src/.env and fill in your API keys"
    Warn "See ENV_SETUP.md for full instructions"
    $continue = Read-Host "  Continue anyway? (y/N)"
    if ($continue -ne "y") { exit 1 }
}

# ─── Check requirements ───────────────────────────────────
$reqFile = Join-Path $RepoRoot "requirements.txt"
if (Test-Path $reqFile) {
    Info "Installing/checking requirements..."
    python -m pip install -r $reqFile --quiet
    Ok "Requirements satisfied"
}

# ─── Set working directory ────────────────────────────────
Set-Location $RepoRoot

# ─── Agent selector ───────────────────────────────────────
$agentMap = @{
    "main"      = "src/main.py"
    "rbi"       = "src/agents/rbi_agent.py"
    "risk"      = "src/agents/risk_agent.py"
    "signal"    = "src/agents/signal_fusion_agent.py"
    "dashboard" = "src/scripts/backtestdashboard.py"
    "trading"   = "src/agents/trading_agent.py"
    "sentiment" = "src/agents/sentiment_agent.py"
    "whale"     = "src/agents/whale_agent.py"
    "funding"   = "src/agents/funding_agent.py"
    "liq"       = "src/agents/liquidation_agent.py"
    "copybot"   = "src/agents/copybot_agent.py"
    "swarm"     = "src/agents/swarm_agent.py"
}

if (-not $agentMap.ContainsKey($Mode)) {
    Err "Unknown mode: $Mode"
    Info "Available modes: $($agentMap.Keys -join ', ')"
    exit 1
}

$script = $agentMap[$Mode]
if (-not (Test-Path $script)) {
    Err "Script not found: $script"
    exit 1
}

# ─── Special messages ─────────────────────────────────────
if ($Mode -eq "dashboard") {
    Info "Starting backtest dashboard..."
    Info "Open browser → http://localhost:8001"
}

if ($Mode -eq "main") {
    Warn "Running full orchestrator. Make sure ACTIVE_AGENTS are configured in src/main.py"
    Warn "All agents are OFF by default — edit src/main.py to enable them"
}

# ─── Launch ───────────────────────────────────────────────
$logDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile   = Join-Path $logDir "${Mode}_${timestamp}.log"

Banner "Launching: python $script"

if ($Background) {
    # Background launch with log capture
    Info "Running in background. Log: $logFile"
    $process = Start-Process python -ArgumentList $script `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError  ($logFile -replace ".log", "_err.log") `
        -PassThru -WindowStyle Hidden
    Ok "Started PID: $($process.Id)"
    Info "To monitor: Get-Content $logFile -Wait"
    Info "To stop:    Stop-Process -Id $($process.Id)"

    # Save PID for watchdog
    $process.Id | Out-File (Join-Path $logDir "bot.pid")
} else {
    # Foreground launch (Ctrl+C to stop)
    Info "Running in foreground. Press Ctrl+C to stop."
    Info "Log also saved to: $logFile"
    python $script 2>&1 | Tee-Object -FilePath $logFile
}
