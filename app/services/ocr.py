"""Image decoding, OpenCV preprocessing and multi-pass Tesseract OCR."""
from typing import Tuple

import cv2
import numpy as np
import pytesseract

from app.config import MAX_IMAGE_DIM, MIN_TEXT_CHARS, OCR_TIMEOUT, TESSERACT_CONFIG


class ImageDecodeError(ValueError):
    """Uploaded bytes are not a readable image."""


class OCRTimeout(RuntimeError):
    """Tesseract exceeded the execution time limit."""


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImageDecodeError("The uploaded file could not be decoded as an image.")
    return img


def scale_down(img: np.ndarray, max_dim: int = MAX_IMAGE_DIM) -> np.ndarray:
    """Shrink (never enlarge) so the longest side is <= max_dim."""
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_dim:
        return img
    ratio = max_dim / float(longest)
    return cv2.resize(img, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)


def preprocess(img: np.ndarray) -> np.ndarray:
    """Grayscale + light edge-preserving denoise."""
    gray = cv2.cvtColor(scale_down(img), cv2.COLOR_BGR2GRAY)
    return cv2.bilateralFilter(gray, 9, 75, 75)


def _tesseract(image: np.ndarray) -> str:
    try:
        return pytesseract.image_to_string(image, config=TESSERACT_CONFIG, timeout=OCR_TIMEOUT)
    except RuntimeError as exc:  # pytesseract raises RuntimeError("Tesseract process timeout")
        if "timeout" in str(exc).lower():
            raise OCRTimeout(f"OCR did not finish within {OCR_TIMEOUT} seconds.") from exc
        raise


def extract_text(data: bytes) -> Tuple[str, int]:
    """Return (text, pass_number). Raises pytesseract.TesseractNotFoundError if the binary is missing."""
    gray = preprocess(decode_image(data))

    # Pass 1 - bilateral-filtered grayscale (best for LSTM engine on natural gradients)
    text = _tesseract(gray)
    if len(text.strip()) >= MIN_TEXT_CHARS:
        return text, 1

    # Pass 2 - Otsu threshold fallback, only when Pass 1 was sparse
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text2 = _tesseract(binary)
    return (text2, 2) if len(text2.strip()) > len(text.strip()) else (text, 1)
