# Run daily PulseGrid pipeline (Windows Task Scheduler).
# Example task: daily 06:00 local, action:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "G:\...\aq-pulsegrid\tools\run_scheduled_pipeline.ps1"

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$python = "python"
if (Test-Path "$Root\.venv\Scripts\python.exe") {
    $python = "$Root\.venv\Scripts\python.exe"
}

& $python "$Root\tools\run_scheduled_pipeline.py" @args
exit $LASTEXITCODE
