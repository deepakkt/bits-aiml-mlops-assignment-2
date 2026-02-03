"""Training entrypoint for the baseline cats vs dogs classifier."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageEnhance
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score

from cats_dogs.data import CLASS_TO_INDEX, DEFAULT_IMAGE_SIZE, load_split_manifest, preprocess_image
from cats_dogs.evaluate import evaluate_from_features
from cats_dogs.model import FeatureConfig, ModelBundle, PreprocessConfig, featurize_image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


DEFAULT_EXPERIMENT_NAME = "cats-dogs-baseline"
DEFAULT_EPOCHS = 8
DEFAULT_BATCH_SIZE = 256
DEFAULT_AUGMENTATIONS_PER_IMAGE = 1


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_metadata(splits_dir: Path) -> dict[str, object]:
    metadata_path = splits_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Expected metadata at {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _augment_image(image: Image.Image, rng: random.Random) -> Image.Image:
    if rng.random() < 0.5:
        image = image.transpose(Image.FLIP_LEFT_RIGHT)

    angle = rng.uniform(-15, 15)
    image = image.rotate(angle)

    brightness = rng.uniform(0.85, 1.15)
    contrast = rng.uniform(0.85, 1.15)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return image


def _build_features(
    items: list[tuple[Path, str]],
    feature_config: FeatureConfig,
    augment: bool,
    augmentations_per_image: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    features: list[np.ndarray] = []
    labels: list[int] = []
    skipped = 0

    for idx, (path, label) in enumerate(items):
        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                base_array = preprocess_image(image)
                features.append(featurize_image(base_array, feature_config))
                labels.append(CLASS_TO_INDEX[label])

                if augment:
                    for aug_idx in range(augmentations_per_image):
                        aug_seed = seed + idx * 1000 + aug_idx
                        rng = random.Random(aug_seed)
                        aug_image = _augment_image(image.copy(), rng)
                        aug_array = preprocess_image(aug_image)
                        features.append(featurize_image(aug_array, feature_config))
                        labels.append(CLASS_TO_INDEX[label])
        except Exception:
            skipped += 1

    if not features:
        raise ValueError("No valid samples available after preprocessing.")

    return np.stack(features), np.array(labels, dtype=np.int64), skipped


def _plot_training_curve(history: dict[str, list[float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    epochs = history["epoch"]
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    ax.plot(epochs, history["train_accuracy"], label="train_acc")
    ax.plot(epochs, history["val_accuracy"], label="val_acc")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy")
    ax.set_title("Training Curve")
    ax.legend()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _resolve_build_info() -> dict[str, str]:
    for key in ("GIT_SHA", "GITHUB_SHA"):
        if os.environ.get(key):
            return {"git_sha": os.environ[key]}
    return {"git_sha": "unknown"}


def main() -> None:
    import warnings

    parser = argparse.ArgumentParser(description="Train baseline model with MLflow logging.")
    parser.add_argument("--splits-dir", default="data/splits")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--bins", type=int, default=FeatureConfig().bins)
    parser.add_argument("--augmentations", type=int, default=DEFAULT_AUGMENTATIONS_PER_IMAGE)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT_NAME)
    parser.add_argument("--mlflow-uri", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"])
    parser.add_argument("--verbose", action="store_true", help="Print per-epoch metrics and progress.")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    repo_root = _resolve_repo_root()
    splits_dir = (repo_root / args.splits_dir).resolve()
    artifacts_dir = (repo_root / args.artifacts_dir).resolve()
    figures_dir = artifacts_dir / "figures"
    model_dir = artifacts_dir / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    metadata = _read_metadata(splits_dir)
    feature_config = FeatureConfig(bins=args.bins)
    preprocess_config = PreprocessConfig(image_size=DEFAULT_IMAGE_SIZE)

    if args.device != "cpu":
        print(
            f"==> Requested device '{args.device}', "
            "but this baseline uses scikit-learn and will run on CPU.",
            flush=True,
        )

    train_items = load_split_manifest(splits_dir / "train.txt")
    val_items = load_split_manifest(splits_dir / "val.txt")
    test_items = load_split_manifest(splits_dir / "test.txt")

    X_train, y_train, skipped_train = _build_features(
        train_items,
        feature_config=feature_config,
        augment=True,
        augmentations_per_image=args.augmentations,
        seed=args.seed,
    )
    X_val, y_val, skipped_val = _build_features(
        val_items,
        feature_config=feature_config,
        augment=False,
        augmentations_per_image=0,
        seed=args.seed,
    )
    X_test, y_test, skipped_test = _build_features(
        test_items,
        feature_config=feature_config,
        augment=False,
        augmentations_per_image=0,
        seed=args.seed,
    )
    if args.verbose:
        print(
            "==> Feature matrices ready: "
            f"train={len(y_train)} (skipped={skipped_train}), "
            f"val={len(y_val)} (skipped={skipped_val}), "
            f"test={len(y_test)} (skipped={skipped_test})",
            flush=True,
        )

    warnings.filterwarnings(
        "ignore",
        message=r"google\.protobuf\.service module is deprecated.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"pkg_resources is deprecated as an API.*",
        category=UserWarning,
    )

    import mlflow

    if args.mlflow_uri:
        mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(args.experiment)

    run_name = args.run_name or f"baseline-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    with mlflow.start_run(run_name=run_name) as run:
        data_source = metadata.get("data_source", {}) if isinstance(metadata, dict) else {}
        mlflow.log_params(
            {
                "seed": args.seed,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "feature_bins": args.bins,
                "augmentations_per_image": args.augmentations,
                "image_size": f"{DEFAULT_IMAGE_SIZE[0]}x{DEFAULT_IMAGE_SIZE[1]}",
                "model_type": "SGDClassifier(log_loss)",
                "device": args.device,
                "train_samples": int(len(y_train)),
                "val_samples": int(len(y_val)),
                "test_samples": int(len(y_test)),
                "skipped_train": skipped_train,
                "skipped_val": skipped_val,
                "skipped_test": skipped_test,
                "split_seed": metadata.get("seed", "unknown") if isinstance(metadata, dict) else "unknown",
                "dataset_root": metadata.get("dataset_root", "unknown")
                if isinstance(metadata, dict)
                else "unknown",
                "data_source_type": data_source.get("type", "unknown"),
                "data_source_path": data_source.get("path", "unknown"),
            }
        )

        clf = SGDClassifier(loss="log_loss", max_iter=1, tol=None, random_state=args.seed)
        classes = np.array(sorted(CLASS_TO_INDEX.values()))
        rng = np.random.default_rng(args.seed)

        history = {"epoch": [], "train_accuracy": [], "val_accuracy": []}
        first_fit = True
        for epoch in range(1, args.epochs + 1):
            indices = rng.permutation(len(y_train))
            for start in range(0, len(y_train), args.batch_size):
                batch_idx = indices[start : start + args.batch_size]
                if first_fit:
                    clf.partial_fit(X_train[batch_idx], y_train[batch_idx], classes=classes)
                    first_fit = False
                else:
                    clf.partial_fit(X_train[batch_idx], y_train[batch_idx])

            train_acc = float(accuracy_score(y_train, clf.predict(X_train)))
            val_acc = float(accuracy_score(y_val, clf.predict(X_val)))

            history["epoch"].append(epoch)
            history["train_accuracy"].append(train_acc)
            history["val_accuracy"].append(val_acc)

            mlflow.log_metric("train_accuracy", train_acc, step=epoch)
            mlflow.log_metric("val_accuracy", val_acc, step=epoch)
            if args.verbose:
                print(
                    f"Epoch {epoch}/{args.epochs} "
                    f"train_acc={train_acc:.4f} val_acc={val_acc:.4f}",
                    flush=True,
                )

        curve_path = figures_dir / "training_curve.png"
        _plot_training_curve(history, curve_path)
        mlflow.log_artifact(str(curve_path))

        class_names = [name for name, _ in sorted(CLASS_TO_INDEX.items(), key=lambda item: item[1])]
        val_results = evaluate_from_features(
            clf,
            X_val,
            y_val,
            class_names=class_names,
            output_dir=figures_dir,
            prefix="val",
        )
        test_results = evaluate_from_features(
            clf,
            X_test,
            y_test,
            class_names=class_names,
            output_dir=figures_dir,
            prefix="test",
        )

        val_metrics = val_results["metrics"]
        test_metrics = test_results["metrics"]

        mlflow.log_metrics(
            {
                "val_accuracy_final": val_metrics["accuracy"],
                "val_precision_final": val_metrics["precision"],
                "val_recall_final": val_metrics["recall"],
                "val_f1_final": val_metrics["f1"],
                "test_accuracy": test_metrics["accuracy"],
                "test_precision": test_metrics["precision"],
                "test_recall": test_metrics["recall"],
                "test_f1": test_metrics["f1"],
            }
        )

        mlflow.log_artifact(str(val_results["confusion_matrix_path"]))
        mlflow.log_artifact(str(test_results["confusion_matrix_path"]))

        metrics_summary = {
            "val": val_metrics,
            "test": test_metrics,
        }

        versions = {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "mlflow": mlflow.__version__,
        }
        try:
            import sklearn

            versions["scikit_learn"] = sklearn.__version__
        except Exception:
            pass
        try:
            import PIL

            versions["pillow"] = PIL.__version__
        except Exception:
            pass

        bundle = ModelBundle(
            classifier=clf,
            class_to_index=CLASS_TO_INDEX,
            index_to_class={v: k for k, v in CLASS_TO_INDEX.items()},
            feature_config=feature_config,
            preprocess_config=preprocess_config,
            training_config={
                "seed": args.seed,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "augmentations_per_image": args.augmentations,
                "feature_bins": args.bins,
                "device": args.device,
            },
            metrics=metrics_summary,
            created_at=datetime.now(timezone.utc).isoformat(),
            mlflow_run_id=run.info.run_id,
            versions=versions,
            build_info=_resolve_build_info(),
        )

        model_path = model_dir / "model.pkl"
        with model_path.open("wb") as handle:
            pickle.dump(bundle, handle)
        mlflow.log_artifact(str(model_path))

    print("==> Training complete")
    print(f"Model saved to: {model_path.relative_to(repo_root)}")
    print(f"Figures saved to: {figures_dir.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
