"""Model and feature utilities for cats vs dogs baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

DEFAULT_FEATURE_BINS = 8


@dataclass(frozen=True)
class FeatureConfig:
    bins: int = DEFAULT_FEATURE_BINS


@dataclass(frozen=True)
class PreprocessConfig:
    image_size: tuple[int, int] = (224, 224)
    normalize: bool = True
    dtype: str = "float32"


@dataclass
class ModelBundle:
    classifier: Any
    class_to_index: dict[str, int]
    index_to_class: dict[int, str]
    feature_config: FeatureConfig
    preprocess_config: PreprocessConfig
    training_config: dict[str, Any]
    metrics: dict[str, float]
    created_at: str
    mlflow_run_id: str | None
    versions: dict[str, str]
    build_info: dict[str, str]
    schema_version: int = 1


def extract_color_histogram(image_array: np.ndarray, bins: int = DEFAULT_FEATURE_BINS) -> np.ndarray:
    """Compute normalized per-channel color histograms as features."""
    if image_array.ndim != 3 or image_array.shape[-1] != 3:
        raise ValueError(f"Expected image array shape (H, W, 3), got {image_array.shape}")

    features: list[np.ndarray] = []
    for channel in range(3):
        hist, _ = np.histogram(image_array[:, :, channel], bins=bins, range=(0.0, 1.0))
        hist = hist.astype(np.float32)
        total = hist.sum()
        if total > 0:
            hist /= total
        features.append(hist)

    return np.concatenate(features, axis=0)


def featurize_image(image_array: np.ndarray, config: FeatureConfig) -> np.ndarray:
    """Convert a preprocessed image array into a feature vector."""
    return extract_color_histogram(image_array, bins=config.bins)
