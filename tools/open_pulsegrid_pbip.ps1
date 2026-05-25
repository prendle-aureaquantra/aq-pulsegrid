# Open platform PulseGrid.pbip for Desktop publish (Fabric embed prerequisite).
$Root = Split-Path -Parent $PSScriptRoot
$Pbip = Join-Path $Root "generated_reports\platform\PulseGrid.pbip"
$Mirror = Join-Path $env:USERPROFILE ".local\aq-pulsegrid\reports\platform\PulseGrid.pbip"
if (Test-Path $Mirror) { $Pbip = $Mirror }
if (-not (Test-Path $Pbip)) { Write-Error "PBIP not found: $Pbip"; exit 1 }
Write-Host "Opening: $Pbip"
Start-Process $Pbip
Write-Host "In Desktop: Load all tables -> Publish -> then run: python tools/publish_pulsegrid_fabric.py"
