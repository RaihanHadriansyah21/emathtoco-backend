# ruff: noqa: E402

import pytest

np = pytest.importorskip("numpy", reason="preprocessing tests require the AI worker image")
cv2 = pytest.importorskip("cv2", reason="preprocessing tests require the AI worker image")

from services.preprocess import (
    SECTION_BINARY_PREFIX,
    _to_section_binary_rgb,
    preprocess_image,
)


def test_section_binary_matches_training_polarity_and_channels() -> None:
    photo = np.full((8, 12, 3), 240, dtype=np.uint8)
    photo[2:6, 5:7] = (20, 30, 25)

    binary_rgb = _to_section_binary_rgb(photo)

    assert binary_rgb.shape == (8, 12, 3)
    assert set(np.unique(binary_rgb).tolist()) == {0, 255}
    assert np.array_equal(binary_rgb[:, :, 0], binary_rgb[:, :, 1])
    assert np.array_equal(binary_rgb[:, :, 1], binary_rgb[:, :, 2])
    assert binary_rgb[0, 0, 0] == 255
    assert binary_rgb[3, 5, 0] == 0


def test_section_binary_uses_nearest_resize_without_second_crop() -> None:
    section = np.full((4, 6, 3), 255, dtype=np.uint8)
    section[0, :] = 0
    section[-1, :] = 0
    section[:, 0] = 0
    section[:, -1] = 0

    actual = preprocess_image(
        section,
        (6, 4),
        f"{SECTION_BINARY_PREFIX}DIVIDE_255",
    )

    assert actual.dtype == np.float32
    assert actual.shape == (1, 4, 6, 3)
    assert set(np.unique(actual).tolist()) == {0.0, 1.0}
    assert np.all(actual[0, 0, :, :] == 0.0)
    assert np.all(actual[0, -1, :, :] == 0.0)
    assert np.all(actual[0, :, 0, :] == 0.0)
    assert np.all(actual[0, :, -1, :] == 0.0)


def test_verified_binary_dataset_sample_is_idempotent() -> None:
    binary = np.array(
        [
            [255, 255, 255, 255],
            [255, 0, 0, 255],
            [255, 255, 255, 255],
        ],
        dtype=np.uint8,
    )
    bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    actual = _to_section_binary_rgb(bgr)

    assert np.array_equal(actual[:, :, 0], binary)
    assert np.array_equal(actual[:, :, 1], binary)
    assert np.array_equal(actual[:, :, 2], binary)
