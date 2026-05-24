# Bundle FastAPI status app + Chicago sample CSVs + platform DimMetro for Lightsail.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Out = Join-Path $Root "publish\linux"
$DataSrc = Join-Path $Root "generated_reports\chicago\data"
$PlatformData = Join-Path $Root "generated_reports\platform\data"
$AppSrc = Join-Path $Root "pulsegrid\web\status_app.py"

if (-not (Test-Path $AppSrc)) { throw "Missing $AppSrc" }
if (-not (Test-Path $PlatformData) -and -not (Test-Path $DataSrc)) {
  throw "Missing platform/chicago data - run: python generate_city.py --platform-only --tier full"
}

Write-Host "Project root: $Root"
Write-Host "Output:       $Out"
if (Test-Path $Out) { Remove-Item -Recurse -Force $Out }
New-Item -ItemType Directory -Force -Path $Out, "$Out\data", "$Out\systemd" | Out-Null

Copy-Item $AppSrc (Join-Path $Out "status_app.py")
Copy-Item (Join-Path $PSScriptRoot "requirements-web.txt") (Join-Path $Out "requirements.txt")
if (Test-Path $PlatformData) {
  Copy-Item (Join-Path $PlatformData "*.csv") (Join-Path $Out "data")
  Write-Host "Included platform CSVs ($((Get-ChildItem (Join-Path $PlatformData '*.csv')).Count) files, multi-metro ML)"
} else {
  Copy-Item (Join-Path $DataSrc "*.csv") (Join-Path $Out "data")
  Write-Warning "Platform data missing; using Chicago sample CSVs only"
}
Copy-Item (Join-Path $PSScriptRoot "aq-pulsegrid.service") (Join-Path $Out "systemd")

$startSh = @'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -r requirements.txt
export PULSEGRID_DATA_DIR="$(pwd)/data"
export PULSEGRID_CITY="${PULSEGRID_CITY:-chicago}"
exec uvicorn status_app:app --host 127.0.0.1 --port 5190
'@
$installSh = @'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
chmod +x start.sh
python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
if command -v sudo >/dev/null 2>&1; then
  sudo cp systemd/aq-pulsegrid.service /etc/systemd/system/aq-pulsegrid.service
  sudo systemctl daemon-reload
  sudo systemctl enable aq-pulsegrid
fi
echo "install-remote.sh done"
'@

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $Out "start.sh"), $startSh, $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $Out "install-remote.sh"), $installSh, $utf8NoBom)
Write-Host "Done. Upload publish/linux to the server (/var/aq-pulsegrid) and run install-remote.sh once."
