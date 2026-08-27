from app.storage.slug import slugify


def test_basic_slug():
    assert slugify("Chicken Teriyaki") == "chicken-teriyaki"


def test_strips_punctuation_and_collapses_separators():
    assert slugify("  Grandma's  BEST!! Pie  ") == "grandma-s-best-pie"


def test_falls_back_when_no_usable_characters():
    assert slugify("!!!") == "recipe"
