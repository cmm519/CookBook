"""Build default pipeline steps from config."""

from __future__ import annotations

from app.config import CookBookConfig
from app.extraction.ollama_formatter import MockFormatterProvider, OllamaFormatterProvider
from app.steps.step01_download import DownloadStep
from app.steps.step02_extract_audio import ExtractAudioStep
from app.steps.step03_transcribe import TranscribeStep
from app.steps.step04_extract_frames import ExtractFramesStep
from app.steps.step05_vision import VisionStep
from app.steps.step06_consolidate import ConsolidateStep
from app.steps.step07_format_recipe import FormatRecipeStep
from app.steps.step08_normalize_markdown import NormalizeMarkdownStep
from app.steps.step09_store_index import StoreIndexStep
from app.vision.tesseract import MockVisionProvider, TesseractVisionProvider
from app.workflow.orchestrator import PipelineOrchestrator


def build_formatter(config: CookBookConfig):
    if config.formatter_provider == "mock":
        return MockFormatterProvider()
    return OllamaFormatterProvider(config.ollama_host, config.formatter_model)


def build_vision(config: CookBookConfig):
    if config.formatter_provider == "mock":
        return MockVisionProvider()
    try:
        return TesseractVisionProvider()
    except RuntimeError:
        return MockVisionProvider()


def build_orchestrator(config: CookBookConfig) -> PipelineOrchestrator:
    formatter = build_formatter(config)
    vision = build_vision(config)
    return PipelineOrchestrator(
        steps=[
            DownloadStep(),
            ExtractAudioStep(),
            TranscribeStep(config),
            ExtractFramesStep(config),
            VisionStep(vision),
            ConsolidateStep(),
            FormatRecipeStep(formatter),
            NormalizeMarkdownStep(),
            StoreIndexStep(config),
        ]
    )
