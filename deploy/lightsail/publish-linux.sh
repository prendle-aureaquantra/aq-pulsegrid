#!/usr/bin/env bash
# Unix publish (same output as publish-linux.ps1)
set -euo pipefail
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
OUT="$ROOT/publish/linux"
DATA_SRC="$ROOT/generated_reports/chicago/data"
APP_SRC="$ROOT/pulsegrid/web/status_app.py"

[[ -f "$APP_SRC" ]] || { echo "Missing $APP_SRC" >&2; exit 1; }
[[ -d "$DATA_SRC" ]] || { echo "Missing $DATA_SRC" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT/data" "$OUT/systemd"
cp "$APP_SRC" "$OUT/status_app.py"
cp "$DEPLOY_DIR/requirements-web.txt" "$OUT/requirements.txt"
cp "$DATA_SRC"/*.csv "$OUT/data/"
cp "$DEPLOY_DIR/aq-pulsegrid.service" "$OUT/systemd/"
cat > "$OUT/install-remote.sh" << 'EOF'
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
EOF
cat > "$OUT/start.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -r requirements.txt
export PULSEGRID_DATA_DIR="$(pwd)/data"
export PULSEGRID_CITY="${PULSEGRID_CITY:-chicago}"
exec uvicorn status_app:app --host 127.0.0.1 --port 5190
EOF
chmod +x "$OUT/start.sh" "$OUT/install-remote.sh"
echo "Published -> $OUT"
