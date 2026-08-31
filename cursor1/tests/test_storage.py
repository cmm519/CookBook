"""Tests for recipe package storage."""

from datetime import UTC, datetime
from pathlib import Path

from app.models import Ingredient, Instruction, Recipe
from app.storage import PackageMetadata, PackageStorage


def test_storage_round_trip(tmp_path: Path):
    storage = PackageStorage(tmp_path)
    recipe = Recipe(
        title="Pasta",
        ingredients=[Ingredient(item="noodles", quantity="1 box")],
        instructions=[Instruction(step=1, text="Cook noodles.")],
        source_url="https://example.com/reel/pasta",
    )
    slug = storage.unique_slug(recipe.title)
    metadata = PackageMetadata(
        source_url=recipe.source_url,
        date_added=datetime.now(UTC).isoformat(),
        slug=slug,
    )
    storage.write_package(slug, recipe=recipe, recipe_md="# Pasta\n", metadata=metadata)
    loaded = storage.read_recipe(slug)
    assert loaded.title == "Pasta"
    assert slug in storage.list_slugs()
