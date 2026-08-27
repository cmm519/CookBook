import pytest
from pydantic import ValidationError

from app.models import Ingredient, Recipe


def test_recipe_round_trips_through_json(sample_recipe):
    dumped = sample_recipe.model_dump_json()
    restored = Recipe.model_validate_json(dumped)
    assert restored == sample_recipe


def test_recipe_requires_title_and_source_url():
    with pytest.raises(ValidationError):
        Recipe(ingredients=[], instructions=[])  # type: ignore[call-arg]


def test_optional_ingredient_fields_default_to_none():
    ing = Ingredient(item="salt")
    assert ing.quantity is None
    assert ing.confidence is None
