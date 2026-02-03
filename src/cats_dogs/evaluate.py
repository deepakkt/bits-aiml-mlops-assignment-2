"""Evaluation utilities for baseline model."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Iterable

import matplotlib
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from cats_dogs.data import CLASS_TO_INDEX, load_split_manifest, preprocess_path
from cats_dogs.model import FeatureConfig, ModelBundle, featurize_image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute accuracy, precision, recall, and F1 (macro)."""
    accuracy = float(accuracy_score(y_true, y_pred))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="macro",
        zero_division=0,
    )
    return {
        "accuracy": accuracy,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[int],
    label_names: list[str],
    output_path: Path,
    title: str,
) -> np.ndarray:
    """Create and save a confusion matrix plot."""
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    fig, ax = plt.subplots(figsize=(4.5, 4.0))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(title)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_xticks(range(len(label_names)), label_names)
    ax.set_yticks(range(len(label_names)), label_names)

    threshold = cm.max() / 2 if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            color = "white" if cm[i, j] > threshold else "black"
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", color=color)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return cm


def evaluate_from_features(
    model,
    features: np.ndarray,
    labels: np.ndarray,
    class_names: list[str],
    output_dir: Path,
    prefix: str,
) -> dict[str, object]:
    """Evaluate a model using precomputed features."""
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = model.predict(features)
    metrics = compute_metrics(labels, predictions)

    cm_path = output_dir / f"confusion_matrix_{prefix}.png"
    cm = plot_confusion_matrix(
        labels,
        predictions,
        labels=list(range(len(class_names))),
        label_names=class_names,
        output_path=cm_path,
        title=f"Confusion Matrix ({prefix})",
    )

    return {"metrics": metrics, "confusion_matrix": cm, "confusion_matrix_path": cm_path}


def _load_features_from_manifest(
    items: Iterable[tuple[Path, str]],
    feature_config: FeatureConfig,
) -> tuple[np.ndarray, np.ndarray, int]:
    features: list[np.ndarray] = []
    labels: list[int] = []
    skipped = 0

    for path, label in items:
        try:
            array = preprocess_path(path)
        except Exception:
            skipped += 1
            continue
        features.append(featurize_image(array, feature_config))
        labels.append(CLASS_TO_INDEX[label])

    if not features:
        raise ValueError("No valid samples found while building features.")

    return np.stack(features), np.array(labels, dtype=np.int64), skipped


def load_model_bundle(model_path: Path) -> ModelBundle:
    with model_path.open("rb") as handle:
        bundle = pickle.load(handle)
    if not isinstance(bundle, ModelBundle):
        raise TypeError("Loaded model is not a ModelBundle. Re-train with the Part 3 pipeline.")
    return bundle


def evaluate_from_manifest(
    bundle: ModelBundle,
    manifest_path: Path,
    output_dir: Path,
    prefix: str,
) -> dict[str, object]:
    items = load_split_manifest(manifest_path)
    features, labels, skipped = _load_features_from_manifest(items, bundle.feature_config)
    class_names = [bundle.index_to_class[i] for i in sorted(bundle.index_to_class.keys())]
    results = evaluate_from_features(
        bundle.classifier,
        features,
        labels,
        class_names=class_names,
        output_dir=output_dir,
        prefix=prefix,
    )
    results["skipped"] = skipped
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a trained model on a dataset split.")
    parser.add_argument("--model-path", default="artifacts/model/model.pkl", help="Path to model.pkl.")
    parser.add_argument(
        "--splits-dir",
        default="data/splits",
        help="Directory containing train/val/test manifest files.",
    )
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--output-dir", default="artifacts/figures")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    output_dir = Path(args.output_dir)
    manifest_path = Path(args.splits_dir) / f"{args.split}.txt"

    bundle = load_model_bundle(model_path)
    results = evaluate_from_manifest(bundle, manifest_path, output_dir, prefix=args.split)
    metrics = results["metrics"]

    print("==> Evaluation complete")
    print(
        f"split={args.split} accuracy={metrics['accuracy']:.4f} "
        f"precision={metrics['precision']:.4f} recall={metrics['recall']:.4f} "
        f"f1={metrics['f1']:.4f} skipped={results['skipped']}"
    )


if __name__ == "__main__":
    main()
