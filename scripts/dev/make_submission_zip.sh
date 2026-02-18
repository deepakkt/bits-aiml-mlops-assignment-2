#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v zip >/dev/null 2>&1; then
  echo "ERROR: zip is not installed or not on PATH." >&2
  exit 1
fi

MODEL_ARTIFACT="${MODEL_ARTIFACT:-artifacts/model/model.pkl}"
if [ ! -f "$MODEL_ARTIFACT" ]; then
  echo "ERROR: Required model artifact not found at ${MODEL_ARTIFACT}" >&2
  echo "Run training first: PYTHONPATH=src python -m cats_dogs.train" >&2
  exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-artifacts/submission}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_ZIP="${OUTPUT_ZIP:-${OUTPUT_DIR}/cats-dogs-mlops-submission-${TIMESTAMP}.zip}"

if [[ "$OUTPUT_ZIP" != /* ]]; then
  OUTPUT_ZIP="${ROOT_DIR}/${OUTPUT_ZIP}"
fi
mkdir -p "$(dirname "$OUTPUT_ZIP")"

INCLUDE_PATHS=(
  app
  src
  scripts
  tests
  .github/workflows
  docker/Dockerfile
  k8s
  argocd
  monitoring
  requirements.txt
  README.md
  state.md
  data/splits
  artifacts/model/model.pkl
)

for path in "${INCLUDE_PATHS[@]}"; do
  if [ ! -e "$path" ]; then
    echo "ERROR: Required submission path missing: ${path}" >&2
    exit 1
  fi
done

if [ -f "$OUTPUT_ZIP" ]; then
  rm -f "$OUTPUT_ZIP"
fi

echo "==> Creating submission archive at ${OUTPUT_ZIP}"
zip -r "$OUTPUT_ZIP" "${INCLUDE_PATHS[@]}" \
  -x '*.DS_Store' \
  -x '*/__pycache__/*' \
  -x '*.pyc' \
  -x '.pytest_cache/*' >/dev/null

echo "==> Submission zip created"
echo "==> Contents preview:"
zipinfo -1 "$OUTPUT_ZIP" | sed -n '1,40p'
