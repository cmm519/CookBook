"""Tests for domain models."""

from app.models import Ingredient, Instruction, Recipe


def test_recipe_validation():
    recipe = Recipe(
        title="Test Soup",
        ingredients=[Ingredient(item="water")],
        instructions=[Instruction(step=1, text="Boil water.")],
        source_url="https://example.com/reel/1",
    )
    assert recipe.title == "Test Soup"


def test_recipe_requires_sequential_steps():
    try:
        Recipe(
            title="Bad",
            ingredients=[Ingredient(item="x")],
            instructions=[Instruction(step=2, text="skip")],
            source_url="https://example.com",
        )
        assert False, "expected validation error"
    except ValueError:
        pass
