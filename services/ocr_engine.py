import os
import logging
from pathlib import Path
import cv2
import numpy as np
import pytesseract
from PIL import Image
from config import TESSERACT_CMD, OCR_LANG

logger = logging.getLogger(__name__)

# Configure Tesseract path if available
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    logger.info(f"Tesseract binary configured at: {TESSERACT_CMD}")
else:
    logger.warning(f"Tesseract binary not found at '{TESSERACT_CMD}'. Relying on PATH.")

class OCREngine:
    def __init__(self, tesseract_cmd: str = TESSERACT_CMD, lang: str = OCR_LANG):
        self.tesseract_cmd = tesseract_cmd
        self.lang = lang

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Applies OpenCV image preprocessing tuned for receipts:
        1. Grayscale conversion
        2. Denoising
        3. CLAHE Contrast Enhancement
        4. Adaptive / Otsu Thresholding
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image from path: {image_path}")

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Resize if too small (scaling factor)
        h, w = gray.shape[:2]
        if w < 1000:
            scale = 1000.0 / w
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        # 3. Denoising
        denoised = cv2.medianBlur(gray, 3)

        # 4. Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(denoised)

        # 5. Otsu Thresholding
        _, thresholded = cv2.threshold(
            contrast_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return thresholded

    def extract_text(self, image_path: str, preprocess: bool = True) -> str:
        """
        Extracts raw text from receipt image using Tesseract OCR.
        """
        try:
            if preprocess:
                processed_img = self.preprocess_image(image_path)
                text = pytesseract.image_to_string(
                    processed_img,
                    lang=self.lang,
                    config="--psm 6 --oem 3"
                )
            else:
                img = Image.open(image_path)
                text = pytesseract.image_to_string(
                    img,
                    lang=self.lang,
                    config="--psm 6 --oem 3"
                )

            # Fallback if PSM 6 yielded little text
            if not text.strip():
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img, lang="eng+ind")

            return text.strip()
        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}")
            return f"OCR Extraction Error: {str(e)}"
