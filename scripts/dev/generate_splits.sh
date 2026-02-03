#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "==> Ensuring virtual environment and dependencies"
./scripts/dev/create_venv.sh

# shellcheck disable=SC1091
echo "==> Generating split manifests"
source .venv/bin/activate
PYTHONPATH=src python -m cats_dogs.data \
  --raw-dir data/raw \
  --splits-dir data/splits \
  --zip-path data/cats-and-dogs-classification-dataset.zip \
  --seed 1337

echo "==> Done"
