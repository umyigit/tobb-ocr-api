from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def preprocess_captcha(image: Image.Image) -> Image.Image:
    """Preprocess captcha image for better OCR: grayscale -> upscale -> threshold -> blur -> sharpen."""
    # Convert to grayscale
    gray = image.convert("L")

    # 2x upscale
    w, h = gray.size
    gray = gray.resize((w * 2, h * 2), Image.LANCZOS)

    # Convert to numpy for OpenCV operations
    arr = np.array(gray)

    # Otsu binary threshold
    _, binary = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Median blur to remove noise
    blurred = cv2.medianBlur(binary, 3)

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(blurred, -1, kernel)

    return Image.fromarray(sharpened)


def preprocess_gazette_page(
    image: Image.Image,
    binarize_block_size: int = 31,
    denoise_strength: int = 10,
) -> Image.Image:
    """Preprocess a gazette page image for OCR.

    Pipeline: grayscale -> denoise -> adaptive binarize -> morphological cleanup.
    """
    gray = image.convert("L")
    arr = np.array(gray)

    # Denoise (skip if strength is 0)
    if denoise_strength > 0:
        arr = cv2.fastNlMeansDenoising(
            arr, None, h=denoise_strength, templateWindowSize=7, searchWindowSize=21
        )

    # Adaptive binarization (handles uneven background from scanning)
    binary = cv2.adaptiveThreshold(
        arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, binarize_block_size, 15
    )

    # Morphological closing to reconnect broken strokes in Turkish diacritics
    kernel = np.ones((2, 2), dtype=np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    return Image.fromarray(closed)


def detect_columns(
    image: Image.Image,
    min_gap_px: int = 4,
) -> list[tuple[int, int]]:
    """Detect column boundaries by finding vertical gaps in pixel density.

    Returns list of (x_start, x_end) tuples for each column.
    Single-column pages return [(0, width)].
    """
    arr = np.array(image.convert("L"))
    width = arr.shape[1]

    # Binarize for density analysis
    _, binary = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Vertical projection profile: sum of dark pixels per x-coordinate
    profile = binary.sum(axis=0).astype(np.float64)

    # Find gaps: regions where density drops below threshold
    mean_density = profile.mean()
    if mean_density == 0:
        return [(0, width)]

    threshold = mean_density * 0.1

    # Search only in center region (30%-70% of page) for column gap
    center_start = int(width * 0.3)
    center_end = int(width * 0.7)

    # Find contiguous below-threshold runs in center region
    best_gap_start = -1
    best_gap_end = -1
    best_gap_width = 0

    gap_start = -1
    for x in range(center_start, center_end):
        if profile[x] < threshold:
            if gap_start == -1:
                gap_start = x
        else:
            if gap_start != -1:
                gap_width = x - gap_start
                if gap_width >= min_gap_px and gap_width > best_gap_width:
                    best_gap_start = gap_start
                    best_gap_end = x
                    best_gap_width = gap_width
                gap_start = -1

    # Check if a run extends to center_end
    if gap_start != -1:
        gap_width = center_end - gap_start
        if gap_width >= min_gap_px and gap_width > best_gap_width:
            best_gap_start = gap_start
            best_gap_end = center_end
            best_gap_width = gap_width

    if best_gap_width < min_gap_px:
        return [(0, width)]

    gap_center = (best_gap_start + best_gap_end) // 2
    return [(0, gap_center), (gap_center, width)]


def split_columns(
    image: Image.Image,
    columns: list[tuple[int, int]],
) -> list[Image.Image]:
    """Crop a page image into individual column images."""
    return [image.crop((x_start, 0, x_end, image.height)) for x_start, x_end in columns]
