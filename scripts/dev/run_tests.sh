#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "==> Ensuring virtual environment and dependencies"
./scripts/dev/create_venv.sh

# shellcheck disable=SC1091
echo "==> Running tests"
source .venv/bin/activate
python -m pytest -q
