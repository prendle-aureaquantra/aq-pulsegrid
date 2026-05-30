#!/usr/bin/env bash
# Unix publish (same output as publish-linux.ps1)
set -euo pipefail
export COPYFILE_DISABLE=1

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
OUT="$ROOT/publish/linux"
DATA_SRC="$ROOT/generated_reports/chicago/data"
PLATFORM_DATA="$ROOT/generated_reports/platform/data"
APP_SRC="$ROOT/pulsegrid/web/status_app.py"
WEB_DIR="$(dirname "$APP_SRC")"

[[ -f "$APP_SRC" ]] || { echo "Missing $APP_SRC" >&2; exit 1; }
if [[ ! -d "$PLATFORM_DATA" && ! -d "$DATA_SRC" ]]; then
  echo "Missing platform/chicago data - run: python generate_city.py --all-metros --platform-csv-only" >&2
  exit 1
fi

VALIDATE="$ROOT/tools/validate_platform_export.py"
if [[ -f "$VALIDATE" && -d "$PLATFORM_DATA" ]]; then
  python3 "$VALIDATE" --data-dir "$PLATFORM_DATA"
fi

echo "Project root: $ROOT"
echo "Output:       $OUT"
rm -rf "$OUT"
mkdir -p "$OUT/data" "$OUT/systemd"

cp "$APP_SRC" "$OUT/status_app.py"
for f in pbi_embed_service.py pbi_embed_page.py copilot_chat.py csv_store.py data_routes.py ml_routes.py; do
  [[ -f "$WEB_DIR/$f" ]] && cp "$WEB_DIR/$f" "$OUT/"
done
PROMPTS_SRC="$ROOT/datasets/reference/synthetic_questions.yaml"
if [[ -f "$PROMPTS_SRC" ]]; then
  cp "$PROMPTS_SRC" "$OUT/synthetic_questions.yaml"
  echo "Included copilot prompts catalog"
fi
cp "$DEPLOY_DIR/requirements-web.txt" "$OUT/requirements.txt"

STATUS_SRC="$ROOT/generated_reports/platform/last_pipeline_run.json"
if [[ -d "$PLATFORM_DATA" ]]; then
  cp "$PLATFORM_DATA"/*.csv "$OUT/data/"
  echo "Included platform CSVs ($(ls "$PLATFORM_DATA"/*.csv 2>/dev/null | wc -l | tr -d ' ') files, multi-metro ML)"
  [[ -f "$STATUS_SRC" ]] && cp "$STATUS_SRC" "$OUT/last_pipeline_run.json"
else
  cp "$DATA_SRC"/*.csv "$OUT/data/"
  echo "WARNING: Platform data missing; using Chicago sample CSVs only"
fi

cp "$DEPLOY_DIR/aq-pulsegrid.service" "$OUT/systemd/"
if [[ -d "$DEPLOY_DIR/systemd" ]]; then
  cp "$DEPLOY_DIR/systemd"/aq-pulsegrid-pipeline.* "$OUT/systemd/" 2>/dev/null || true
fi

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

chmod +x "$OUT/start.sh" "$OUT/install-remote.sh"
echo "Done. Upload publish/linux to the server (/var/aq-pulsegrid) and run install-remote.sh once."
