# ============================================================
# Moon Dev Bot - Windows Launch Script
# ============================================================
# Usage:
#   .\start_bot.ps1              (foreground, full orchestrator)
#   .\start_bot.ps1 -Background  (background with PID logging)
#   .\start_bot.ps1 -Mode rbi    (just the RBI backtest pipeline)
#
# Modes: main, rbi, risk, signal, dashboard, trading, sentiment,
#        whale, funding, liq, copybot, swarm
# ============================================================

param(
    [string]$Mode = "main",
    [switch]$Background = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$SrcDir   = Join-Path $RepoRoot "src"

function Info  ($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok    ($msg) { Write-Host "  OK: $msg" -ForegroundColor Green }
function Warn  ($msg) { Write-Host "  WARN: $msg" -ForegroundColor Yellow }
function Err   ($msg) { Write-Host "  ERROR: $msg" -ForegroundColor Red }
function Banner($msg) { Write-Host "" ; Write-Host "  *** $msg ***" -ForegroundColor White -BackgroundColor DarkBlue ; Write-Host "" }

Banner "Moon Dev AI Trading Bot"
Info "Mode: $Mode"
Info "Repo: $RepoRoot"

# Check Python
try {
    $pyver = python --version 2>&1
    Ok "Python: $pyver"
} catch {
    Err "Python not found."
    exit 1
}

# Check .env
$envFile = Join-Path $SrcDir ".env"
if (-not (Test-Path $envFile)) {
    Warn ".env not found at $envFile"
    Warn "Copy src/.env_example to src/.env and fill in your API keys"
    $continue = Read-Host "  Continue anyway? (y/N)"
    if ($continue -ne "y") { exit 1 }
}

# Set working directory, PYTHONPATH, and UTF-8 encoding (fixes Windows emoji issues)
Set-Location $RepoRoot
$env:PYTHONPATH  = $RepoRoot
$env:PYTHONUTF8  = "1"
$env:PYTHONIOENCODING = "utf-8"

# Agent selector
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
    Info "Available: $($agentMap.Keys -join ', ')"
    exit 1
}

$script = $agentMap[$Mode]
if (-not (Test-Path $script)) {
    Err "Script not found: $script"
    exit 1
}

# Log directory
$logDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile   = Join-Path $logDir "${Mode}_${timestamp}.log"
$errFile   = Join-Path $logDir "${Mode}_${timestamp}_err.log"

Banner "Launching: python $script"

if ($Background) {
    Info "Running in background..."
    Info "Log: $logFile"
    $process = Start-Process python -ArgumentList $script `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError  $errFile `
        -PassThru -WindowStyle Hidden
    Ok "Started PID: $($process.Id)"
    Info "Monitor: Get-Content $logFile -Wait"
    Info "Stop:    Stop-Process -Id $($process.Id)"
    $process.Id | Out-File (Join-Path $logDir "bot.pid")
    Ok "PID saved to logs\bot.pid"
} else {
    Info "Running in foreground. Ctrl+C to stop."
    Info "Log: $logFile"
    python $script 2>&1 | Tee-Object -FilePath $logFile
}
