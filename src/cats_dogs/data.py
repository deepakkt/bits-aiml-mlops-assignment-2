"""Data utilities for dataset prep and preprocessing."""

from __future__ import annotations

import argparse
import json
import random
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

DEFAULT_SEED = 1337
DEFAULT_IMAGE_SIZE = (224, 224)
DEFAULT_SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}
CLASS_TO_INDEX = {"cat": 0, "dog": 1}


def preprocess_image(image: Image.Image, size: tuple[int, int] = DEFAULT_IMAGE_SIZE) -> np.ndarray:
    """Convert to RGB, resize, and scale to [0, 1] float32."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    try:
        resample = Image.Resampling.BILINEAR
    except AttributeError:
        resample = Image.BILINEAR

    image = image.resize(size, resample=resample)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return array


def preprocess_path(path: Path, size: tuple[int, int] = DEFAULT_IMAGE_SIZE) -> np.ndarray:
    """Load an image from disk and preprocess it."""
    with Image.open(path) as image:
        return preprocess_image(image, size=size)


def _infer_label_from_parts(parts: Iterable[str]) -> str | None:
    for part in reversed(list(parts)):
        lower = part.lower()
        if lower in {"cat", "cats"}:
            return "cat"
        if lower in {"dog", "dogs"}:
            return "dog"
    return None


def _is_image_name(name: str) -> bool:
    return Path(name).suffix.lower() in SUPPORTED_SUFFIXES


def _has_class_dirs(candidate: Path) -> bool:
    if not candidate.is_dir():
        return False
    names = {child.name.lower() for child in candidate.iterdir() if child.is_dir()}
    return bool(names.intersection({"cat", "cats"})) and bool(names.intersection({"dog", "dogs"}))


def _find_dataset_root(raw_dir: Path) -> Path:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {raw_dir}")

    if _has_class_dirs(raw_dir):
        return raw_dir

    for candidate in raw_dir.rglob("*"):
        if _has_class_dirs(candidate):
            return candidate

    raise FileNotFoundError(
        f"Could not find class directories under {raw_dir}. Expected cat/dog folders."
    )


def _collect_from_directory(raw_dir: Path) -> tuple[dict[str, list[Path]], Path]:
    dataset_root = _find_dataset_root(raw_dir)
    paths_by_label: dict[str, list[Path]] = {"cat": [], "dog": []}
    for path in dataset_root.rglob("*"):
        if not path.is_file():
            continue
        if not _is_image_name(path.name):
            continue
        label = _infer_label_from_parts(path.parts)
        if label is None:
            continue
        paths_by_label[label].append(path)

    if not any(paths_by_label.values()):
        raise FileNotFoundError(f"No images found under {dataset_root}")

    return paths_by_label, dataset_root


def _collect_from_zip(zip_path: Path, raw_dir: Path) -> tuple[dict[str, list[Path]], Path]:
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    paths_by_label: dict[str, list[Path]] = {"cat": [], "dog": []}
    root_candidates: set[str] = set()

    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            if not _is_image_name(name):
                continue
            parts = name.split("/")
            if parts:
                root_candidates.add(parts[0])
            label = _infer_label_from_parts(parts)
            if label is None:
                continue
            paths_by_label[label].append(raw_dir / name)

    if not any(paths_by_label.values()):
        raise FileNotFoundError(f"No images found inside zip: {zip_path}")

    dataset_root = raw_dir / root_candidates.pop() if len(root_candidates) == 1 else raw_dir
    return paths_by_label, dataset_root


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: Path, repo_root: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _stratified_split(
    paths_by_label: dict[str, list[Path]],
    seed: int,
    ratios: dict[str, float],
) -> dict[str, list[tuple[Path, str]]]:
    splits: dict[str, list[tuple[Path, str]]] = {"train": [], "val": [], "test": []}

    for label in sorted(paths_by_label.keys()):
        paths = sorted(paths_by_label[label], key=lambda p: p.as_posix())
        rng = random.Random(f"{seed}:{label}")
        rng.shuffle(paths)

        total = len(paths)
        train_count = int(total * ratios["train"])
        val_count = int(total * ratios["val"])
        test_count = total - train_count - val_count

        splits["train"].extend((path, label) for path in paths[:train_count])
        splits["val"].extend((path, label) for path in paths[train_count : train_count + val_count])
        splits["test"].extend((path, label) for path in paths[train_count + val_count :])

    for split in splits:
        splits[split] = sorted(splits[split], key=lambda item: item[0].as_posix())

    return splits


def write_split_manifests(
    raw_dir: Path,
    splits_dir: Path,
    seed: int = DEFAULT_SEED,
    ratios: dict[str, float] | None = None,
    zip_path: Path | None = None,
) -> dict[str, object]:
    ratios = ratios or DEFAULT_SPLIT_RATIOS
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"Split ratios must sum to 1.0, got {ratios}")

    repo_root = _resolve_repo_root()
    raw_dir_abs = _resolve_path(raw_dir, repo_root)
    splits_dir_abs = _resolve_path(splits_dir, repo_root)

    paths_by_label: dict[str, list[Path]]
    dataset_root: Path
    source: dict[str, str]

    try:
        paths_by_label, dataset_root = _collect_from_directory(raw_dir_abs)
        source = {"type": "filesystem", "path": dataset_root.relative_to(repo_root).as_posix()}
    except FileNotFoundError:
        if zip_path is None:
            raise
        zip_path_abs = _resolve_path(zip_path, repo_root)
        paths_by_label, dataset_root = _collect_from_zip(zip_path_abs, raw_dir_abs)
        source = {"type": "zip", "path": zip_path_abs.relative_to(repo_root).as_posix()}

    splits = _stratified_split(paths_by_label, seed=seed, ratios=ratios)

    splits_dir_abs.mkdir(parents=True, exist_ok=True)

    counts_by_class: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}

    for split_name, items in splits.items():
        output_path = splits_dir_abs / f"{split_name}.txt"
        lines: list[str] = []
        class_counts = {"cat": 0, "dog": 0}
        for path, label in items:
            rel_path = path.relative_to(repo_root).as_posix()
            lines.append(f"{rel_path}\t{label}")
            class_counts[label] += 1
        output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        counts_by_class[split_name] = class_counts
        counts[split_name] = len(items)

    metadata = {
        "seed": seed,
        "ratios": ratios,
        "counts": counts,
        "counts_by_class": counts_by_class,
        "class_to_index": CLASS_TO_INDEX,
        "label_inference": "Label inferred from any path segment named cat/cats or dog/dogs (case-insensitive).",
        "manifest_format": "path\\tlabel (repo-relative path)",
        "data_source": source,
        "raw_dir": raw_dir_abs.relative_to(repo_root).as_posix(),
        "dataset_root": dataset_root.relative_to(repo_root).as_posix(),
        "supported_suffixes": sorted(SUPPORTED_SUFFIXES),
    }

    metadata_path = splits_dir_abs / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic split manifests.")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory with extracted dataset.")
    parser.add_argument("--splits-dir", default="data/splits", help="Output directory for manifests.")
    parser.add_argument(
        "--zip-path",
        default="data/cats-and-dogs-classification-dataset.zip",
        help="Optional zip to read if raw dataset is not extracted.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed for splits.")
    args = parser.parse_args()

    metadata = write_split_manifests(
        raw_dir=Path(args.raw_dir),
        splits_dir=Path(args.splits_dir),
        seed=args.seed,
        zip_path=Path(args.zip_path) if args.zip_path else None,
    )
    counts = metadata["counts"]
    print(
        "==> Wrote manifests:",
        f"train={counts['train']}, val={counts['val']}, test={counts['test']}",
    )


if __name__ == "__main__":
    main()
