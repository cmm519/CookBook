"""Tests for shopping list."""

from datetime import UTC, datetime
from pathlib import Path

from app.models import Ingredient, Instruction, Recipe
from app.shopping.list import build_shopping_list
from app.storage import PackageMetadata, PackageStorage


def test_shopping_list_merge(tmp_path: Path):
    storage = PackageStorage(tmp_path)
    now = datetime.now(UTC).isoformat()
    for title, slug, item in [
        ("Recipe A", "recipe-a", "garlic"),
        ("Recipe B", "recipe-b", "garlic"),
    ]:
        recipe = Recipe(
            title=title,
            ingredients=[
                Ingredient(item=item, quantity="2 cloves" if slug == "recipe-a" else "1 head")
            ],
            instructions=[Instruction(step=1, text="Mix.")],
            source_url=f"https://example.com/{slug}",
        )
        storage.write_package(
            slug,
            recipe=recipe,
            recipe_md="# x\n",
            metadata=PackageMetadata(source_url=recipe.source_url, date_added=now, slug=slug),
        )
    items = build_shopping_list(storage, ["recipe-a", "recipe-b"])
    assert len(items) == 1
    assert "garlic" in items[0].ingredient_name.lower()
    assert len(items[0].source_recipe_slugs) == 2
