"""Tesseract OCR vision provider."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.models import VisionEvidence, VisionFrameEvidence
from app.vision.provider import VisionProvider


class TesseractVisionProvider(VisionProvider):
    """OCR via pytesseract + system tesseract binary."""

    def __init__(self) -> None:
        if shutil.which("tesseract") is None:
            raise RuntimeError("tesseract binary not found")

    def analyze_frames(self, frame_paths: list[Path]) -> VisionEvidence:
        import pytesseract
        from PIL import Image

        frames: list[VisionFrameEvidence] = []
        for index, frame_path in enumerate(frame_paths):
            text = pytesseract.image_to_string(Image.open(frame_path)).strip()
            if text:
                frames.append(
                    VisionFrameEvidence(
                        timestamp=float(index * 2),
                        text=text,
                        confidence=0.8,
                    )
                )
        combined = "\n".join(frame.text for frame in frames)
        return VisionEvidence(frames=frames, combined_text=combined)


class MockVisionProvider(VisionProvider):
    """Test double returning fixture text."""

    def __init__(self, combined_text: str = "2 tbsp soy sauce") -> None:
        self._combined_text = combined_text

    def analyze_frames(self, frame_paths: list[Path]) -> VisionEvidence:
        if not frame_paths:
            return VisionEvidence()
        return VisionEvidence(
            frames=[
                VisionFrameEvidence(timestamp=0.0, text=self._combined_text, confidence=1.0)
            ],
            combined_text=self._combined_text,
        )
