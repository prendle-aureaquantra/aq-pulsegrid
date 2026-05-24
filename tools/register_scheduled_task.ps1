# Register daily PulseGrid pipeline on Windows Task Scheduler (06:00 local).
# Run once as Administrator if Register-ScheduledTask fails without elevation.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Root "tools\run_scheduled_pipeline.ps1"
$TaskName = "AQ-PulseGrid-Daily-Pipeline"

if (-not (Test-Path $Script)) {
    Write-Error "Missing $Script"
}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $Root

$Trigger = New-ScheduledTaskTrigger -Daily -At "06:00"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "AQ PulseGrid: ingest, transform, ML, platform export" `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily 06:00)"
Write-Host "Test now: powershell -File `"$Script`""
Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
