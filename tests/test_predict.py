"""Unit tests for inference utilities."""

from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from cats_dogs.model import FeatureConfig, ModelBundle, PreprocessConfig  # noqa: E402
from cats_dogs.predict import predict_image  # noqa: E402


class DummyClassifier:
    def __init__(self, probs: list[float], classes: list[int]) -> None:
        self._probs = np.array([probs], dtype=np.float32)
        self.classes_ = np.array(classes)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:  # noqa: N803 - match sklearn signature
        return np.repeat(self._probs, X.shape[0], axis=0)


def test_predict_image_returns_label_and_probability() -> None:
    bundle = ModelBundle(
        classifier=DummyClassifier([0.2, 0.8], classes=[0, 1]),
        class_to_index={"cat": 0, "dog": 1},
        index_to_class={0: "cat", 1: "dog"},
        feature_config=FeatureConfig(bins=8),
        preprocess_config=PreprocessConfig(image_size=(224, 224), normalize=True, dtype="float32"),
        training_config={},
        metrics={},
        created_at="2024-01-01T00:00:00Z",
        mlflow_run_id=None,
        versions={},
        build_info={},
    )

    image = Image.new("RGB", (128, 128), color=(255, 0, 0))
    result = predict_image(bundle, image)

    assert result.label == "dog"
    assert abs(result.probability - 0.8) < 1e-6
