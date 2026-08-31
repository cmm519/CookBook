"""Vision/OCR provider interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from app.models import VisionEvidence


class VisionProvider(ABC):
    @abstractmethod
    def analyze_frames(self, frame_paths: list[Path]) -> VisionEvidence:
        """Extract on-screen text from video frames."""
