#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is not installed or not on PATH." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is not installed or not on PATH." >&2
  exit 1
fi

API_URL="${API_URL:-http://localhost:8000}"
MANIFEST_PATH="${MANIFEST_PATH:-data/splits/test.txt}"
SAMPLE_SIZE="${SAMPLE_SIZE:-20}"
REPORT_DIR="${REPORT_DIR:-artifacts/reports}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_CSV="${OUTPUT_CSV:-${REPORT_DIR}/post_deploy_eval_${TIMESTAMP}.csv}"

mkdir -p "$REPORT_DIR"

python3 - "$ROOT_DIR" "$API_URL" "$MANIFEST_PATH" "$SAMPLE_SIZE" "$OUTPUT_CSV" <<'PY'
import csv
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


repo_root = Path(sys.argv[1])
api_url = sys.argv[2].rstrip("/")
manifest_path = repo_root / sys.argv[3]
sample_size = int(sys.argv[4])
output_csv = Path(sys.argv[5])

if sample_size <= 0:
    raise SystemExit("ERROR: SAMPLE_SIZE must be > 0.")
if not manifest_path.exists():
    raise SystemExit(f"ERROR: Manifest not found at {manifest_path}")

health_url = f"{api_url}/health"
try:
    with urlopen(health_url, timeout=10) as response:  # nosec B310 (trusted local URL)
        payload = json.loads(response.read().decode("utf-8"))
except (HTTPError, URLError, TimeoutError) as exc:
    raise SystemExit(f"ERROR: Could not reach {health_url}: {exc}") from exc

if payload.get("status") != "ok":
    raise SystemExit(f"ERROR: API health is not ok: {payload}")

rows: list[tuple[Path, str]] = []
for line in manifest_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    rel_path, label = line.split("\t", 1)
    rows.append((repo_root / rel_path, label))

if not rows:
    raise SystemExit(f"ERROR: Manifest {manifest_path} has no data.")

cats = [item for item in rows if item[1] == "cat"]
dogs = [item for item in rows if item[1] == "dog"]
half = sample_size // 2

selected: list[tuple[Path, str]] = []
selected.extend(cats[:half])
selected.extend(dogs[:half])

remaining = sample_size - len(selected)
if remaining > 0:
    leftovers = cats[half:] + dogs[half:]
    selected.extend(leftovers[:remaining])

if not selected:
    raise SystemExit("ERROR: No samples selected for evaluation.")

predict_url = f"{api_url}/predict"
report_rows: list[dict[str, str]] = []

for image_path, true_label in selected:
    row = {
        "record_type": "sample",
        "sample_path": str(image_path.relative_to(repo_root)),
        "true_label": true_label,
        "predicted_label": "",
        "probability": "",
        "correct": "",
        "accuracy": "",
        "evaluated": "",
        "total": "",
        "error_count": "",
        "error": "",
    }

    if not image_path.exists():
        row["error"] = "image_not_found"
        report_rows.append(row)
        continue

    result = subprocess.run(
        ["curl", "-fsS", "-F", f"file=@{image_path}", predict_url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        row["error"] = f"request_failed:{result.stderr.strip()}"
        report_rows.append(row)
        continue

    try:
        payload = json.loads(result.stdout)
        pred_label = str(payload["label"])
        probability = float(payload["probability"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        row["error"] = f"invalid_response:{exc}"
        report_rows.append(row)
        continue

    correct = int(pred_label == true_label)
    row["predicted_label"] = pred_label
    row["probability"] = f"{probability:.6f}"
    row["correct"] = str(correct)
    report_rows.append(row)

evaluated = sum(1 for r in report_rows if r["correct"] in {"0", "1"})
correct_count = sum(int(r["correct"]) for r in report_rows if r["correct"] in {"0", "1"})
error_count = len(report_rows) - evaluated
accuracy = (correct_count / evaluated) if evaluated else 0.0

summary = {
    "record_type": "summary",
    "sample_path": "",
    "true_label": "",
    "predicted_label": "",
    "probability": "",
    "correct": str(correct_count),
    "accuracy": f"{accuracy:.6f}",
    "evaluated": str(evaluated),
    "total": str(len(report_rows)),
    "error_count": str(error_count),
    "error": "",
}
report_rows.append(summary)

output_csv.parent.mkdir(parents=True, exist_ok=True)
with output_csv.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "record_type",
            "sample_path",
            "true_label",
            "predicted_label",
            "probability",
            "correct",
            "accuracy",
            "evaluated",
            "total",
            "error_count",
            "error",
        ],
    )
    writer.writeheader()
    writer.writerows(report_rows)

print(f"==> Wrote post-deploy evaluation report: {output_csv}")
print(f"==> Evaluated={evaluated} Correct={correct_count} Accuracy={accuracy:.4f} Errors={error_count}")
PY
