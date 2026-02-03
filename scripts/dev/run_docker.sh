#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  exit 1
fi

IMAGE_NAME_BASE="cats-dogs-classifier"
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-local}"
IMAGE_TAG="${IMAGE_TAG:-local}"
IMAGE_NAME="docker.io/${DOCKERHUB_USERNAME}/${IMAGE_NAME_BASE}"

CONTAINER_NAME="${CONTAINER_NAME:-cats-dogs-api}"
HOST_PORT="${HOST_PORT:-8000}"

MODEL_PATH="${MODEL_PATH:-artifacts/model/model.pkl}"
if [ ! -f "$MODEL_PATH" ]; then
  echo "ERROR: model artifact not found at $MODEL_PATH" >&2
  echo "Run training first: PYTHONPATH=src python -m cats_dogs.train" >&2
  exit 1
fi

echo "==> Building image ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -f docker/Dockerfile -t "${IMAGE_NAME}:${IMAGE_TAG}" .

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "==> Removing existing container ${CONTAINER_NAME}"
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "==> Running container ${CONTAINER_NAME} on port ${HOST_PORT}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:8000" \
  -e MODEL_PATH="${MODEL_PATH}" \
  "${IMAGE_NAME}:${IMAGE_TAG}" >/dev/null

echo "==> Container is running"
echo "    Health: http://localhost:${HOST_PORT}/health"
