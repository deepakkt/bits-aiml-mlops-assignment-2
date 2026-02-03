#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required for smoke tests." >&2
  exit 1
fi

API_URL="${API_URL:-http://localhost:8000}"
HEALTH_URL="${API_URL}/health"
PREDICT_URL="${API_URL}/predict"

MAX_RETRIES="${MAX_RETRIES:-15}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t cats-dogs-smoke)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

HEALTH_OUT="$TMP_DIR/health.json"
PREDICT_OUT="$TMP_DIR/predict.json"
IMAGE_PATH="$TMP_DIR/smoke.png"

export IMAGE_PATH
export HEALTH_OUT
export PREDICT_OUT
python3 - <<'PY'
import base64
import os
from pathlib import Path

payload = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO/1F5sAAAAASUVORK5CYII="
)
Path(os.environ["IMAGE_PATH"]).write_bytes(base64.b64decode(payload))
PY

echo "==> Waiting for API: ${HEALTH_URL}"
for attempt in $(seq 1 "$MAX_RETRIES"); do
  if curl -fsS "$HEALTH_URL" -o "$HEALTH_OUT"; then
    break
  fi
  echo "==> Health check attempt ${attempt}/${MAX_RETRIES} failed, retrying..."
  sleep "$SLEEP_SECONDS"
  if [ "$attempt" -eq "$MAX_RETRIES" ]; then
    echo "ERROR: API did not become healthy." >&2
    exit 1
  fi
done

python3 - <<'PY'
import json
import os
from pathlib import Path

health = json.loads(Path(os.environ["HEALTH_OUT"]).read_text())
status = health.get("status")
if status != "ok":
    raise SystemExit(f"Health status not ok: {health}")
PY

echo "==> Calling predict endpoint"
if ! curl -fsS -F "file=@${IMAGE_PATH}" "$PREDICT_URL" -o "$PREDICT_OUT"; then
  echo "ERROR: Predict request failed." >&2
  exit 1
fi

python3 - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["PREDICT_OUT"]).read_text())
if "label" not in data or "probability" not in data:
    raise SystemExit(f"Unexpected predict response: {data}")
PY

echo "==> Smoke test passed"
