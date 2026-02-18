# ============================================================
# 🌙 Moon Dev Bot — Watchdog Script
# Called by OpenClaw cron to check bot health & report status
# ============================================================
# Returns JSON to stdout for OpenClaw to parse:
#   { "status": "running|stopped|error", "pid": int|null,
#     "uptime_min": int, "log_tail": str, "action": str }
# ============================================================

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir   = Join-Path $RepoRoot "logs"
$PidFile  = Join-Path $LogDir "bot.pid"

$result = @{
    status     = "unknown"
    pid        = $null
    uptime_min = 0
    log_tail   = ""
    action     = "none"
    timestamp  = (Get-Date -Format "o")
}

# ─── Check if PID file exists ─────────────────────────────
if (Test-Path $PidFile) {
    $savedPid = [int](Get-Content $PidFile -Raw).Trim()
    $proc = Get-Process -Id $savedPid -ErrorAction SilentlyContinue

    if ($proc) {
        $uptime = [int]((Get-Date) - $proc.StartTime).TotalMinutes
        $result.status     = "running"
        $result.pid        = $savedPid
        $result.uptime_min = $uptime
        $result.action     = "monitoring"
    } else {
        # Process died — restart it
        $result.status = "stopped"
        $result.action = "restarting"

        $logFile = Join-Path $LogDir ("main_watchdog_restart_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
        Set-Location $RepoRoot
        $newProc = Start-Process python -ArgumentList "src/main.py" `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError  ($logFile -replace ".log", "_err.log") `
            -PassThru -WindowStyle Hidden
        $newProc.Id | Out-File $PidFile
        $result.pid = $newProc.Id
    }
} else {
    $result.status = "not_started"
    $result.action = "pid_file_missing"
}

# ─── Grab last 5 lines of most recent log ─────────────────
if (Test-Path $LogDir) {
    $latestLog = Get-ChildItem $LogDir -Filter "main_*.log" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latestLog) {
        $tail = Get-Content $latestLog.FullName -Tail 5 -ErrorAction SilentlyContinue
        $result.log_tail = ($tail -join "`n")
    }
}

# ─── Output JSON ──────────────────────────────────────────
$result | ConvertTo-Json -Compress
