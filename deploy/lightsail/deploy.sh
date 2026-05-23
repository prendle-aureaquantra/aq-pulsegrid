#!/usr/bin/env bash
set -euo pipefail
export COPYFILE_DISABLE=1

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DEPLOY_DIR/../.." && pwd)"
PUBLISH="$ROOT/publish/linux"
ENV_FILE="$DEPLOY_DIR/deploy.config.env"
SKIP_PUBLISH=0
DRY_RUN=0

for a in "$@"; do
  case "$a" in
    --skip-publish) SKIP_PUBLISH=1 ;;
    --dry-run) DRY_RUN=1 ;;
  esac
done

load_env() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$f"
  set +a
}

load_env "$ENV_FILE"
strip_cr() { printf '%s' "${1//$'\r'/}"; }

USER_NAME="$(strip_cr "${AQ_LIGHTSAIL_USER:-bitnami}")"
REMOTE_DIR="$(strip_cr "${AQ_LIGHTSAIL_REMOTE_DIR:-/var/aq-pulsegrid}")"
HOST="$(strip_cr "${AQ_LIGHTSAIL_HOST:-}")"

if [[ -z "$HOST" && -n "${AQ_LIGHTSAIL_INSTANCE_NAME:-}" ]]; then
  HOST="$(aws lightsail get-instance --instance-name "$AQ_LIGHTSAIL_INSTANCE_NAME" --query 'instance.publicIpAddress' --output text)"
fi
[[ -n "$HOST" && "$HOST" != "None" ]] || { echo "Set AQ_LIGHTSAIL_HOST in deploy.config.env" >&2; exit 1; }

KEY_RAW="${AQ_LIGHTSAIL_KEY:-secrets/lightsail-key.pem}"
if [[ "$KEY_RAW" = /* ]]; then KEY_PATH="$KEY_RAW"; else KEY_PATH="$DEPLOY_DIR/$KEY_RAW"; fi
[[ -f "$KEY_PATH" ]] || { echo "SSH key not found: $KEY_PATH" >&2; exit 1; }

SSH=(ssh -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new "${USER_NAME}@${HOST}")

if [[ "$SKIP_PUBLISH" -eq 0 ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then echo "[dry-run] publish-linux.ps1"; else pwsh -NoProfile -File "$DEPLOY_DIR/publish-linux.ps1" 2>/dev/null || bash "$DEPLOY_DIR/publish-linux.sh"; fi
fi
[[ -d "$PUBLISH" ]] || { echo "Missing $PUBLISH"; exit 1; }

REMOTE_INIT="sudo mkdir -p ${REMOTE_DIR} && sudo chown -R ${USER_NAME}:${USER_NAME} ${REMOTE_DIR}"
if [[ "$DRY_RUN" -eq 1 ]]; then echo "[dry-run] upload"; else
  "${SSH[@]}" "$REMOTE_INIT"
  (cd "$PUBLISH" && tar -cf - .) | "${SSH[@]}" "tar -xf - -C ${REMOTE_DIR}"
  PG_ENV="$DEPLOY_DIR/secrets/pulsegrid.env"
  if [[ -f "$PG_ENV" ]]; then
    "${SSH[@]}" "mkdir -p ${REMOTE_DIR}/secrets && chmod 700 ${REMOTE_DIR}/secrets"
    scp -i "$KEY_PATH" -o StrictHostKeyChecking=accept-new "$PG_ENV" "${USER_NAME}@${HOST}:${REMOTE_DIR}/secrets/pulsegrid.env"
  fi
  "${SSH[@]}" "cd ${REMOTE_DIR} && chmod +x start.sh install-remote.sh && ./install-remote.sh"
  "${SSH[@]}" "sudo systemctl restart aq-pulsegrid; curl -sf http://127.0.0.1:5190/health || true"
fi
echo "Done. http://${HOST}:5190/"
