"""
OCR Node — Step 1 of the BGV pipeline.

Accepts an uploaded file (PDF or image), applies OpenCV preprocessing,
runs Tesseract, and writes raw_text to state.
"""

import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.graph.state import VerificationState


def _preprocess_image(img_array: np.ndarray) -> np.ndarray:
    """
    OpenCV pipeline:
    1. Grayscale
    2. Bilateral filter (denoise while preserving edges)
    3. Adaptive threshold (handles uneven lighting)
    4. Deskew
    """
    # 1. Grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    # 2. Bilateral filter
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 3. Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2,
    )

    # 4. Deskew
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.5:  # Only rotate if skew is significant
            h, w = thresh.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

    return thresh


def _extract_text_from_image(img_array: np.ndarray) -> str:
    """Run Tesseract on a preprocessed image array."""
    preprocessed = _preprocess_image(img_array)
    # Convert back to PIL for Tesseract
    pil_img = Image.fromarray(preprocessed)
    config = "--oem 3 --psm 3"  # LSTM engine, fully automatic page segmentation
    return pytesseract.image_to_string(pil_img, config=config)


def ocr_node(state: VerificationState) -> dict:
    """
    LangGraph node: reads document_url from state, extracts text.
    Handles both PDFs (via pdf2image) and images directly.
    """
    file_path = state.get("document_url", "")
    reasoning = list(state.get("reasoning", []))

    reasoning.append(f"[OCR] Processing file: {Path(file_path).name}")

    try:
        ext = Path(file_path).suffix.lower()
        all_text_parts = []

        if ext == ".pdf":
            reasoning.append("[OCR] Detected PDF — converting pages to images")
            pages = convert_from_path(file_path, dpi=300)
            for i, page in enumerate(pages):
                img_array = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
                page_text = _extract_text_from_image(img_array)
                all_text_parts.append(page_text)
                reasoning.append(f"[OCR] Extracted text from page {i + 1} ({len(page_text)} chars)")
        else:
            reasoning.append("[OCR] Detected image — running directly through Tesseract")
            img_array = cv2.imread(file_path)
            if img_array is None:
                raise ValueError(f"Could not read image file: {file_path}")
            page_text = _extract_text_from_image(img_array)
            all_text_parts.append(page_text)
            reasoning.append(f"[OCR] Extracted {len(page_text)} characters")

        raw_text = "\n\n".join(all_text_parts).strip()

        if not raw_text:
            reasoning.append("[OCR] Warning: No text extracted — document may be blank or corrupt")
            raw_text = ""

        reasoning.append(f"[OCR] Complete. Total characters: {len(raw_text)}")
        return {"raw_text": raw_text, "reasoning": reasoning}

    except Exception as e:
        reasoning.append(f"[OCR] Error: {str(e)} — setting raw_text to empty string")
        return {"raw_text": "", "reasoning": reasoning}
