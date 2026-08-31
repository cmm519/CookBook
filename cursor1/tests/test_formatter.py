"""Tests for mock formatter and consolidation."""

from app.extraction.consolidate import build_consolidated_input
from app.extraction.ollama_formatter import MockFormatterProvider
from app.models import ConsolidatedSourceInput


def test_mock_formatter_produces_recipe():
    consolidated = build_consolidated_input(
        source_url="https://example.com/reel/x",
        raw_transcript="Add two cups flour and mix.",
    )
    recipe = MockFormatterProvider().format_recipe(consolidated)
    assert recipe.source_url == consolidated.source_url
    assert len(recipe.ingredients) >= 1
