"""Central configuration + cross-platform Tesseract discovery."""
import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Optional

import pytesseract

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("nutritruth")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

APP_NAME = "NutriTruth Lite"
MAX_IMAGE_DIM = 1600            # px - longest side after down-scaling
OCR_TIMEOUT = 10                # seconds per Tesseract call
MIN_TEXT_CHARS = 25             # below this, Pass 1 is considered "sparse"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
TESSERACT_CONFIG = "--oem 3 --psm 6"


def find_tesseract() -> Optional[str]:
    """Return the path of the Tesseract binary, or None if it cannot be found."""
    override = os.environ.get("TESSERACT_CMD")
    if override and Path(override).is_file():
        return override

    on_path = shutil.which("tesseract")
    if on_path:
        return on_path

    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(os.path.join(local, "Programs", "Tesseract-OCR", "tesseract.exe"))
    else:  # Linux / macOS
        candidates = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",   # Apple-silicon Homebrew
        ]
    for path in candidates:
        if Path(path).is_file():
            return path
    return None


def install_hint() -> str:
    system = platform.system()
    if system == "Windows":
        return ("Tesseract OCR was not found. Install it from "
                "https://github.com/UB-Mannheim/tesseract/wiki (default path "
                "C:\\Program Files\\Tesseract-OCR), or set the TESSERACT_CMD "
                "environment variable to tesseract.exe, then restart the server.")
    if system == "Darwin":
        return ("Tesseract OCR was not found. Install it with 'brew install tesseract' "
                "and restart the server (or set TESSERACT_CMD).")
    return ("Tesseract OCR was not found. Install it with "
            "'sudo apt-get install tesseract-ocr' (Debian/Ubuntu), "
            "'sudo dnf install tesseract' (Fedora) or 'sudo pacman -S tesseract' (Arch), "
            "then restart the server (or set TESSERACT_CMD).")


def configure_tesseract() -> Optional[str]:
    """Resolve the binary, point pytesseract at it and log the result."""
    path = find_tesseract()
    if path:
        pytesseract.pytesseract.tesseract_cmd = path
        logger.info("Tesseract binary resolved to: %s", path)
    else:
        logger.warning("Tesseract binary NOT FOUND. %s", install_hint())
    return path
