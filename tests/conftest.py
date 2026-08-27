import pytest

from app.models import Ingredient, Instruction, Recipe


@pytest.fixture
def sample_recipe() -> Recipe:
    return Recipe(
        title="Miso Glazed Salmon",
        description="Sweet-savory miso glaze on flaky salmon.",
        servings="2 servings",
        prep_time="5 min",
        cook_time="12 min",
        total_time="17 min",
        ingredients=[
            Ingredient(item="salmon fillets", quantity="2"),
            Ingredient(item="white miso", quantity="2 tbsp"),
            Ingredient(item="honey", quantity="1 tbsp"),
        ],
        instructions=[
            Instruction(step=2, text="Broil until caramelized.", duration="8 min"),
            Instruction(step=1, text="Whisk miso and honey, then coat the salmon."),
        ],
        notes=["Rest for 2 minutes before serving."],
        tags=["asian", "seafood"],
        source_url="https://www.instagram.com/reel/ABC123/",
        source_creator="test-creator",
    )
