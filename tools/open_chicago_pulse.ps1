# Open ChicagoPulse.pbip in Power BI Desktop (required before Fabric/browser viewing).
$pbip = Join-Path $env:USERPROFILE ".local\aq-pulsegrid\reports\chicago\ChicagoPulse.pbip"
if (-not (Test-Path $pbip)) {
    Write-Host "PBIP not found. Run: python generate_city.py --city chicago --pbip-only"
    exit 1
}

$desktop = @(
    "${env:ProgramFiles}\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
    "${env:ProgramFiles(x86)}\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
    "${env:LOCALAPPDATA}\Microsoft\WindowsApps\PBIDesktopStore.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($desktop) {
    Write-Host "Opening in Power BI Desktop: $pbip"
    Start-Process -FilePath $desktop -ArgumentList $pbip
} else {
    Write-Host "Power BI Desktop not found. Open manually:"
    Write-Host $pbip
    Start-Process $pbip
}

Write-Host ""
Write-Host "After it loads: File -> Publish -> pick a workspace."
Write-Host "Do NOT expect app.powerbi.com to open .pbip files directly."
