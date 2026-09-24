import os
import pytest
import numpy as np
from services.ocr_engine import OCREngine
from config import TESSERACT_CMD

def test_ocr_engine_initialization():
    engine = OCREngine()
    assert engine.tesseract_cmd is not None
    assert engine.lang == "ind+eng"

def test_opencv_preprocessing_on_synthetic_image(tmp_path):
    import cv2
    # Create a small dummy image with text
    img_path = str(tmp_path / "test_receipt.png")
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TOTAL 50.000", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.imwrite(img_path, img)

    ocr = OCREngine()
    processed = ocr.preprocess_image(img_path)
    assert processed is not None
    assert isinstance(processed, np.ndarray)
    assert processed.shape[0] > 0

    # Extract text if Tesseract binary is present
    if os.path.exists(TESSERACT_CMD):
        text = ocr.extract_text(img_path, preprocess=True)
        assert len(text) > 0
