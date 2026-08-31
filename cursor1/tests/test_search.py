"""Tests for SQLite search index."""

from datetime import UTC, datetime
from pathlib import Path

from app.models import Ingredient, Instruction, Recipe
from app.search.sqlite_index import RecipeIndex


def test_search_index(tmp_path: Path):
    db = tmp_path / "recipes.db"
    index = RecipeIndex(db)
    recipe = Recipe(
        title="Chicken Curry",
        ingredients=[Ingredient(item="chicken", quantity="1 lb")],
        instructions=[Instruction(step=1, text="Cook chicken.")],
        source_url="https://example.com/reel/curry",
    )
    now = datetime.now(UTC).isoformat()
    index.upsert("chicken-curry", recipe, updated_at=now)
    hits = index.search("chicken")
    assert len(hits) == 1
    assert hits[0]["slug"] == "chicken-curry"
