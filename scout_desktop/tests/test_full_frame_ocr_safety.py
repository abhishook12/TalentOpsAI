from __future__ import annotations

import time

from PIL import Image

from scout_desktop.core.ocr_engine import OcrEngine


def test_busy_ocr_never_reuses_text_from_a_previous_screenshot(tmp_path):
    """A new frame must wait, never inherit OCR lines from an old page."""
    image_path = tmp_path / "fresh-page.png"
    Image.new("RGB", (64, 64), "white").save(image_path)
    engine = OcrEngine()
    engine._last_lines = ["Old Person", "Old Company"]
    engine._last_ocr_time = time.time()

    assert engine.extract_text_from_image(str(image_path)) == []


def test_large_screens_still_receive_ocr_cleanup(tmp_path):
    """Large screenshots keep native resolution but are not returned untouched."""
    image_path = tmp_path / "large-page.png"
    Image.new("RGB", (2400, 1400), "white").save(image_path)
    engine = OcrEngine()

    prepared = engine._preprocess_for_ocr(str(image_path))
    assert prepared != str(image_path)
