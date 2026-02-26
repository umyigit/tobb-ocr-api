from __future__ import annotations

import numpy as np
from PIL import Image

from app.utils.image_processing import (
    detect_columns,
    preprocess_gazette_page,
    split_columns,
)


class TestPreprocessGazettePage:
    def test_returns_grayscale(self):
        """Output should be a grayscale (mode L) image."""
        img = Image.new("RGB", (100, 100), "gray")
        result = preprocess_gazette_page(img)
        assert result.mode == "L"

    def test_preserves_dimensions(self):
        """Output size should match input size."""
        img = Image.new("RGB", (200, 300), "white")
        result = preprocess_gazette_page(img)
        assert result.size == (200, 300)

    def test_binarized_output(self):
        """Output should be binary (only 0 and 255 pixel values)."""
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        result = preprocess_gazette_page(img)
        arr = np.array(result)
        unique_vals = set(np.unique(arr))
        assert unique_vals.issubset({0, 255})

    def test_no_denoise_when_zero(self):
        """With denoise_strength=0, denoising step is skipped without error."""
        img = Image.new("RGB", (100, 100), "white")
        result = preprocess_gazette_page(img, denoise_strength=0)
        assert result.mode == "L"


class TestDetectColumns:
    def test_single_column_page(self):
        """Uniform white image should be detected as single column."""
        img = Image.new("L", (200, 300), 255)
        columns = detect_columns(img)
        assert len(columns) == 1
        assert columns[0] == (0, 200)

    def test_two_column_page(self):
        """Image with clear vertical gap should be split into two columns."""
        arr = np.full((300, 200), 255, dtype=np.uint8)
        # Dense dark pixels in left column (x: 10-90)
        arr[10:290, 10:90] = 0
        # Dense dark pixels in right column (x: 110-190)
        arr[10:290, 110:190] = 0
        # Gap at x: 90-110 (20px wide, center at 100)
        img = Image.fromarray(arr)
        columns = detect_columns(img, min_gap_px=4)
        assert len(columns) == 2
        gap_center = columns[0][1]
        assert 95 <= gap_center <= 105

    def test_narrow_gap_ignored(self):
        """Gap narrower than min_gap_px should not cause a split."""
        arr = np.full((300, 200), 255, dtype=np.uint8)
        arr[10:290, 10:98] = 0
        arr[10:290, 100:190] = 0  # only 2px gap at x:98-100
        img = Image.fromarray(arr)
        columns = detect_columns(img, min_gap_px=4)
        assert len(columns) == 1

    def test_gap_outside_center_ignored(self):
        """Gaps outside the 30%-70% center region are not used as column splits."""
        arr = np.full((300, 200), 255, dtype=np.uint8)
        # Dense text across full width except gap at x:10-30 (left margin, outside center)
        arr[10:290, 30:190] = 0
        img = Image.fromarray(arr)
        columns = detect_columns(img, min_gap_px=4)
        assert len(columns) == 1


class TestSplitColumns:
    def test_single_column_identity(self):
        """Single column returns the full image."""
        img = Image.new("RGB", (200, 300), "white")
        result = split_columns(img, [(0, 200)])
        assert len(result) == 1
        assert result[0].size == (200, 300)

    def test_two_columns_sizes(self):
        """Two columns should produce correctly sized crops."""
        img = Image.new("RGB", (200, 300), "white")
        result = split_columns(img, [(0, 100), (100, 200)])
        assert len(result) == 2
        assert result[0].size == (100, 300)
        assert result[1].size == (100, 300)
