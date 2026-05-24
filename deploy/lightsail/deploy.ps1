<#
.SYNOPSIS
  Publish PulseGrid status app, upload to Lightsail over SSH, restart systemd unit.
#>
param(
  [switch]$SkipPublish,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$DeployDir = $PSScriptRoot
$ProjectRoot = Resolve-Path (Join-Path $DeployDir "..\..")
$PublishOut = Join-Path $ProjectRoot "publish\linux"
$EnvFile = Join-Path $DeployDir "deploy.config.env"
$SecretsDir = Join-Path $DeployDir "secrets"

function Import-DotEnvFile {
  param([Parameter(Mandatory)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return }
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line.Length -eq 0 -or $line.StartsWith("#")) { return }
    $i = $line.IndexOf("=")
    if ($i -lt 1) { return }
    $name = $line.Substring(0, $i).Trim()
    $val = $line.Substring($i + 1).Trim().Trim([char]0x0D)
    if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
      $val = $val.Substring(1, $val.Length - 2)
    }
    Set-Item -Path "env:$name" -Value $val
  }
}

Import-DotEnvFile -Path $EnvFile

$remoteUser = ($env:AQ_LIGHTSAIL_USER -replace "`r", "").Trim()
if ([string]::IsNullOrWhiteSpace($remoteUser)) { $remoteUser = "bitnami" }

$remoteDir = ($env:AQ_LIGHTSAIL_REMOTE_DIR -replace "`r", "").Trim()
if ([string]::IsNullOrWhiteSpace($remoteDir)) { $remoteDir = "/var/aq-pulsegrid" }

$hostAddr = ($env:AQ_LIGHTSAIL_HOST -replace "`r", "").Trim()
if ([string]::IsNullOrWhiteSpace($hostAddr) -and -not [string]::IsNullOrWhiteSpace($env:AQ_LIGHTSAIL_INSTANCE_NAME)) {
  Write-Host "Resolving public IP via AWS CLI for instance '$($env:AQ_LIGHTSAIL_INSTANCE_NAME)'..."
  if ($DryRun) { Write-Host "[dry-run] aws lightsail get-instance ..." }
  else {
    $hostAddr = aws lightsail get-instance --instance-name $env:AQ_LIGHTSAIL_INSTANCE_NAME --query "instance.publicIpAddress" --output text
    $hostAddr = ($hostAddr -replace "`r", "").Trim()
    if ([string]::IsNullOrWhiteSpace($hostAddr) -or $hostAddr -eq "None") {
      throw "Could not resolve public IP. Set AQ_LIGHTSAIL_HOST or fix AWS CLI / instance name."
    }
  }
}

if ([string]::IsNullOrWhiteSpace($hostAddr)) {
  throw "Set AQ_LIGHTSAIL_HOST or AQ_LIGHTSAIL_INSTANCE_NAME in deploy.config.env."
}

$keyRaw = ($env:AQ_LIGHTSAIL_KEY -replace "`r", "").Trim()
if ([string]::IsNullOrWhiteSpace($keyRaw)) { throw "Set AQ_LIGHTSAIL_KEY in deploy.config.env." }

$keyPath = if ([System.IO.Path]::IsPathRooted($keyRaw)) { $keyRaw } else { Join-Path $DeployDir $keyRaw }
if (-not (Test-Path -LiteralPath $keyPath)) { throw "SSH key not found: $keyPath" }

$sshBase = @("-i", $keyPath, "-o", "StrictHostKeyChecking=accept-new", "${remoteUser}@${hostAddr}")
$scpBase = @("-i", $keyPath, "-o", "StrictHostKeyChecking=accept-new", "-B")

if (-not $SkipPublish) {
  Write-Host "Publishing -> $PublishOut"
  if ($DryRun) { Write-Host "[dry-run] publish-linux.ps1" }
  else { & (Join-Path $DeployDir "publish-linux.ps1") }
}

if (-not (Test-Path -LiteralPath $PublishOut)) { throw "Publish output missing: $PublishOut" }

$remoteInit = "set -e; sudo mkdir -p '$remoteDir'; sudo chown -R '$remoteUser':'$remoteUser' '$remoteDir'"
Write-Host "Ensuring remote dir ownership: $remoteDir"
if ($DryRun) { Write-Host "[dry-run] ssh ... $remoteInit" }
else {
  & ssh @sshBase $remoteInit
  if ($LASTEXITCODE -ne 0) { throw "Remote mkdir/chown failed (ssh exit $LASTEXITCODE)" }
}

Write-Host "Uploading -> ${remoteUser}@${hostAddr}:$remoteDir"
if ($DryRun) { Write-Host "[dry-run] upload publish/linux -> remote" }
else {
  $winTar = (Get-Command tar -ErrorAction SilentlyContinue)
  $scpCmd = (Get-Command scp -ErrorAction SilentlyContinue)
  if ($winTar -and $scpCmd) {
    $tmpTgz = Join-Path $env:TEMP ("aq-pulsegrid-" + [guid]::NewGuid().ToString("n") + ".tar.gz")
    $remoteTgz = "/tmp/aq-pulsegrid-" + [guid]::NewGuid().ToString("n") + ".tar.gz"
    try {
      & tar -czf $tmpTgz -C $PublishOut .
      if ($LASTEXITCODE -ne 0) { throw "Local tar.gz failed" }
      & scp @scpBase $tmpTgz "${remoteUser}@${hostAddr}:$remoteTgz"
      if ($LASTEXITCODE -ne 0) { throw "scp upload failed" }
      $extract = "sudo tar -xzf '$remoteTgz' -C '$remoteDir' && sudo rm -f '$remoteTgz' && sudo chown -R '$remoteUser':'$remoteUser' '$remoteDir' && chmod +x '$remoteDir/start.sh' '$remoteDir/install-remote.sh'"
      & ssh @sshBase $extract
      if ($LASTEXITCODE -ne 0) { throw "Remote extract failed" }
    }
    finally {
      if (Test-Path -LiteralPath $tmpTgz) { Remove-Item -LiteralPath $tmpTgz -Force -ErrorAction SilentlyContinue }
    }
  }
  elseif (Get-Command rsync -ErrorAction SilentlyContinue) {
    & rsync -avz --delete -e "ssh -i `"$keyPath`" -o StrictHostKeyChecking=accept-new" "$PublishOut/" "${remoteUser}@${hostAddr}:$remoteDir/"
    if ($LASTEXITCODE -ne 0) { throw "rsync upload failed" }
  }
  else { throw "Need tar+scp or rsync on PATH." }
}

$pgEnvLocal = Join-Path $SecretsDir "pulsegrid.env"
if (Test-Path -LiteralPath $pgEnvLocal) {
  Write-Host "Uploading secrets/pulsegrid.env ..."
  if (-not $DryRun) {
    & ssh @sshBase "mkdir -p '$remoteDir/secrets' && chmod 700 '$remoteDir/secrets'"
    & scp @scpBase $pgEnvLocal "${remoteUser}@${hostAddr}:${remoteDir}/secrets/pulsegrid.env"
    & ssh @sshBase "chmod 600 '$remoteDir/secrets/pulsegrid.env'"
  }
}

$bootstrap = "cd '$remoteDir' && chmod +x start.sh install-remote.sh && ./install-remote.sh"
Write-Host "Installing / refreshing remote venv + systemd unit..."
if ($DryRun) { Write-Host "[dry-run] ssh ... $bootstrap" }
else {
  & ssh @sshBase $bootstrap
  if ($LASTEXITCODE -ne 0) { Write-Warning "install-remote.sh returned exit $LASTEXITCODE" }
}

$restart = "sudo systemctl restart aq-pulsegrid 2>/dev/null || true; sudo systemctl status aq-pulsegrid --no-pager || true; curl -sf http://127.0.0.1:5190/health || true"
Write-Host "Restarting service aq-pulsegrid..."
if ($DryRun) { Write-Host "[dry-run] ssh restart" }
else {
  & ssh @sshBase $restart
}

Write-Host "Done."
Write-Host "PulseGrid status: http://${hostAddr}:5190/ (open port 5190 in Lightsail networking if needed)"
Write-Host "Health: http://${hostAddr}:5190/health"
