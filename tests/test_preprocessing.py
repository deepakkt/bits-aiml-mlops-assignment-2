"""Unit tests for preprocessing utilities."""

from pathlib import Path
import sys

from PIL import Image
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from cats_dogs.data import preprocess_image  # noqa: E402


def test_preprocess_image_shape_dtype_range() -> None:
    image = Image.new("L", (300, 200), color=128)
    array = preprocess_image(image)

    assert array.shape == (224, 224, 3)
    assert array.dtype == np.float32
    assert array.min() >= 0.0
    assert array.max() <= 1.0
