"""Inference utilities for the cats vs dogs classifier."""

from __future__ import annotations

import io
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from cats_dogs.data import preprocess_image
from cats_dogs.model import ModelBundle, PreprocessConfig, featurize_image


class ModelLoadError(RuntimeError):
    """Raised when the model bundle cannot be loaded."""


@dataclass(frozen=True)
class PredictionResult:
    label: str
    probability: float
    probabilities: dict[str, float]


def load_model_bundle(model_path: Path) -> ModelBundle:
    """Load a ModelBundle from disk."""
    if not model_path.exists():
        raise ModelLoadError(f"Model not found at {model_path}")
    with model_path.open("rb") as handle:
        bundle = pickle.load(handle)
    if not isinstance(bundle, ModelBundle):
        raise ModelLoadError("Loaded object is not a ModelBundle. Re-train with Part 3 pipeline.")
    return bundle


def _preprocess_for_inference(image: Image.Image, config: PreprocessConfig) -> np.ndarray:
    array = preprocess_image(image, size=config.image_size)
    if not config.normalize:
        array = array * 255.0
    dtype = np.dtype(config.dtype)
    if array.dtype != dtype:
        array = array.astype(dtype)
    return array


def _scores_to_proba(scores: np.ndarray) -> np.ndarray:
    if scores.ndim == 1:
        scores = scores.reshape(-1, 1)
    if scores.shape[1] == 1:
        probs_pos = 1.0 / (1.0 + np.exp(-scores[:, 0]))
        probs = np.stack([1.0 - probs_pos, probs_pos], axis=1)
    else:
        scores = scores - scores.max(axis=1, keepdims=True)
        exp_scores = np.exp(scores)
        probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    return probs


def _predict_proba(classifier: Any, features: np.ndarray) -> np.ndarray:
    features = features.reshape(1, -1)
    if hasattr(classifier, "predict_proba"):
        proba = classifier.predict_proba(features)
    elif hasattr(classifier, "decision_function"):
        scores = classifier.decision_function(features)
        proba = _scores_to_proba(np.asarray(scores))
    else:
        preds = classifier.predict(features)
        classes = getattr(classifier, "classes_", np.unique(preds))
        proba = np.zeros((features.shape[0], len(classes)), dtype=np.float32)
        for idx, pred in enumerate(preds):
            class_index = list(classes).index(pred)
            proba[idx, class_index] = 1.0
    return np.asarray(proba, dtype=np.float32)


def _resolve_class_labels(bundle: ModelBundle, classifier: Any, n_classes: int) -> list[str]:
    class_indices = getattr(classifier, "classes_", None)
    if class_indices is None:
        class_indices = list(range(n_classes))
    labels: list[str] = []
    for cls in class_indices:
        try:
            key = int(cls)
        except (TypeError, ValueError):
            key = cls
        labels.append(bundle.index_to_class.get(key, str(cls)))
    if len(labels) != n_classes:
        labels = [str(idx) for idx in range(n_classes)]
    return labels


def predict_image(bundle: ModelBundle, image: Image.Image) -> PredictionResult:
    """Run inference on a PIL image and return the predicted label/probability."""
    array = _preprocess_for_inference(image, bundle.preprocess_config)
    features = featurize_image(array, bundle.feature_config)
    proba = _predict_proba(bundle.classifier, features)
    if proba.ndim == 1:
        proba = proba.reshape(1, -1)
    scores = proba[0]
    labels = _resolve_class_labels(bundle, bundle.classifier, len(scores))
    probabilities = {label: float(score) for label, score in zip(labels, scores)}
    best_idx = int(np.argmax(scores))
    return PredictionResult(
        label=labels[best_idx],
        probability=float(scores[best_idx]),
        probabilities=probabilities,
    )


def predict_bytes(bundle: ModelBundle, payload: bytes) -> PredictionResult:
    """Run inference on raw image bytes."""
    if not payload:
        raise ValueError("Empty image payload.")
    with Image.open(io.BytesIO(payload)) as image:
        return predict_image(bundle, image)


def predict_path(bundle: ModelBundle, path: Path) -> PredictionResult:
    """Run inference on an image path."""
    with Image.open(path) as image:
        return predict_image(bundle, image)
