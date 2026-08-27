from app.formatting import render_markdown
from app.models import Recipe


def test_markdown_has_expected_sections(sample_recipe):
    md = render_markdown(sample_recipe)
    assert md.startswith("# Miso Glazed Salmon")
    assert "## Ingredients" in md
    assert "## Instructions" in md
    assert "## Source" in md
    assert "[Original Video](https://www.instagram.com/reel/ABC123/)" in md


def test_instructions_render_in_step_order(sample_recipe):
    md = render_markdown(sample_recipe)
    first = md.index("1. Whisk miso")
    second = md.index("2. Broil until caramelized")
    assert first < second


def test_optional_sections_are_omitted_when_empty():
    recipe = Recipe(title="Plain Toast", source_url="https://youtu.be/xyz")
    md = render_markdown(recipe)
    assert "## Ingredients" not in md
    assert "## Time" not in md
    assert md.endswith("[Original Video](https://youtu.be/xyz)\n")


def test_render_is_deterministic(sample_recipe):
    assert render_markdown(sample_recipe) == render_markdown(sample_recipe)
