"""
CircuitSathi OCR Module
Provides OCR fallback for scanned pages using pytesseract and PIL.
Safely detects whether Tesseract is installed without crashing.
"""

import io
from typing import Optional
from PIL import Image

try:
    import pytesseract
    # Check if pytesseract is executable
    _TESSERACT_AVAILABLE = True
except Exception:
    _TESSERACT_AVAILABLE = False


def is_ocr_available() -> bool:
    """Check if Tesseract OCR binary is found and working."""
    if not _TESSERACT_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_text_from_image(image_bytes: bytes) -> tuple[str, bool]:
    """
    Extract text from raw image bytes.
    Returns (extracted_text, success_flag).
    """
    if not is_ocr_available():
        return ("", False)
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Convert to grayscale for better OCR accuracy
        gray = image.convert("L")
        text = pytesseract.image_to_string(gray)
        return (text.strip(), True)
    except Exception as e:
        return (f"[OCR Error: {str(e)}]", False)
