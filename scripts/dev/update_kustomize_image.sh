#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

KUSTOMIZATION_FILE="${KUSTOMIZATION_FILE:-k8s/overlays/dev/kustomization.yaml}"

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <image_repo> <image_tag>" >&2
  exit 1
fi

IMAGE_REPO="$1"
IMAGE_TAG="$2"

if [ ! -f "$KUSTOMIZATION_FILE" ]; then
  echo "ERROR: kustomization file not found at ${KUSTOMIZATION_FILE}" >&2
  exit 1
fi

if ! grep -q '^[[:space:]]*newName:' "$KUSTOMIZATION_FILE"; then
  echo "ERROR: newName field not found in ${KUSTOMIZATION_FILE}" >&2
  exit 1
fi

if ! grep -q '^[[:space:]]*newTag:' "$KUSTOMIZATION_FILE"; then
  echo "ERROR: newTag field not found in ${KUSTOMIZATION_FILE}" >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

awk -v image_repo="$IMAGE_REPO" -v image_tag="$IMAGE_TAG" '
{
  if ($1 == "newName:") {
    indent = substr($0, 1, index($0, "n") - 1)
    print indent "newName: " image_repo
    next
  }
  if ($1 == "newTag:") {
    indent = substr($0, 1, index($0, "n") - 1)
    print indent "newTag: " image_tag
    next
  }
  print
}
' "$KUSTOMIZATION_FILE" > "$tmp_file"

mv "$tmp_file" "$KUSTOMIZATION_FILE"
trap - EXIT

echo "Updated ${KUSTOMIZATION_FILE} -> ${IMAGE_REPO}:${IMAGE_TAG}"
