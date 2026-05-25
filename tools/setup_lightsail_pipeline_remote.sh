#!/usr/bin/env bash
# Run on Lightsail (or via: ssh ... 'bash -s' < setup_lightsail_pipeline_remote.sh)
set -euo pipefail

REMOTE_DIR="${AQ_PULSEGRID_REMOTE_DIR:-/var/aq-pulsegrid}"
REPO_URL="${AQ_PULSEGRID_REPO_URL:-https://github.com/prendle-aureaquantra/aq-pulsegrid.git}"
REPO_DIR="$REMOTE_DIR/repo"
PIPE_DATA="$REMOTE_DIR/pipeline-data"

sudo mkdir -p "$REMOTE_DIR" "$PIPE_DATA"
sudo chown -R "$(whoami):$(whoami)" "$REMOTE_DIR" "$PIPE_DATA"

if ! command -v git >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone --depth 1 "$REPO_URL" "$REPO_DIR"
else
  git -C "$REPO_DIR" fetch --depth 1 origin main
  git -C "$REPO_DIR" checkout main
  git -C "$REPO_DIR" pull --ff-only origin main || true
fi

cd "$REPO_DIR"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q deltalake pandas pyarrow requests pyyaml python-dotenv httpx 2>/dev/null || true
export PYTHONPATH="$REPO_DIR"

if [[ -f "$REMOTE_DIR/systemd/aq-pulsegrid-pipeline.service" ]]; then
  sudo cp "$REMOTE_DIR/systemd/aq-pulsegrid-pipeline.service" /etc/systemd/system/
  sudo cp "$REMOTE_DIR/systemd/aq-pulsegrid-pipeline.timer" /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable aq-pulsegrid-pipeline.timer
  sudo systemctl start aq-pulsegrid-pipeline.timer
  systemctl list-timers aq-pulsegrid-pipeline.timer --no-pager || true
fi

echo "Lightsail pipeline repo ready at $REPO_DIR"
