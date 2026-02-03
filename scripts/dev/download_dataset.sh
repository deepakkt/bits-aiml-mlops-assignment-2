#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RAW_DIR="data/raw"
ZIP_PATH="data/cats-and-dogs-classification-dataset.zip"
DATASET_SLUG="${KAGGLE_DATASET:-tawsifurrahman/cats-and-dogs-classification-dataset}"

echo "==> Preparing dataset directories"
mkdir -p "$RAW_DIR"

if [ -d "$RAW_DIR/PetImages" ]; then
  echo "==> Dataset already extracted at $RAW_DIR/PetImages"
  exit 0
fi

if [ ! -f "$ZIP_PATH" ]; then
  echo "==> Dataset zip not found; attempting Kaggle download"
  echo "==> Ensuring virtual environment and dependencies"
  ./scripts/dev/create_venv.sh

  # shellcheck disable=SC1091
  source .venv/bin/activate

  if [ ! -f "$HOME/.kaggle/kaggle.json" ] && { [ -z "${KAGGLE_USERNAME:-}" ] || [ -z "${KAGGLE_KEY:-}" ]; }; then
    echo "ERROR: Kaggle credentials not found. Provide ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY." >&2
    exit 1
  fi

  echo "==> Downloading Kaggle dataset: $DATASET_SLUG"
  python -m kaggle datasets download -d "$DATASET_SLUG" -p data
else
  echo "==> Found existing dataset zip at $ZIP_PATH"
fi

if [ ! -f "$ZIP_PATH" ]; then
  echo "ERROR: Expected dataset zip at $ZIP_PATH but it was not found." >&2
  exit 1
fi

echo "==> Extracting dataset to $RAW_DIR"
unzip -q -o "$ZIP_PATH" -d "$RAW_DIR"

if [ -d "$RAW_DIR/PetImages" ]; then
  echo "==> Dataset ready at $RAW_DIR/PetImages"
else
  echo "WARNING: Expected PetImages directory not found after extraction. Check contents of $RAW_DIR." >&2
fi

echo "==> Done"
