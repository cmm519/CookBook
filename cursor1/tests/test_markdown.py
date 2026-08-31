"""Tests for markdown formatting."""

from app.formatting.markdown import normalize_recipe, recipe_to_markdown
from app.models import Ingredient, Instruction, Recipe


def test_markdown_golden():
    recipe = Recipe(
        title="Garlic Toast",
        ingredients=[Ingredient(item="bread"), Ingredient(item="garlic", quantity="2 cloves")],
        instructions=[Instruction(step=1, text="Toast bread.")],
        source_url="https://example.com/reel/toast",
    )
    recipe = normalize_recipe(recipe)
    md = recipe_to_markdown(recipe)
    assert "# Garlic Toast" in md
    assert "## Ingredients" in md
    assert "2 cloves garlic" in md
    assert "1. Toast bread." in md
