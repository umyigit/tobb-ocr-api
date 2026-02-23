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
