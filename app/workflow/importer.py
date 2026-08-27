"""Store-and-index orchestration for a validated recipe.

The full URL -> recipe pipeline (download, audio, transcription, vision, LLM
extraction) is composed from the provider interfaces in the sibling packages.
This module implements the deterministic tail of the pipeline that has no
network or model dependency: persist a validated recipe and index it for
search.
"""

from __future__ import annotations

from pathlib import Path

from app.models import Recipe
from app.search import RecipeSearchIndex
from app.storage import RecipeRepository, StoredRecipe


def import_recipe(
    recipe: Recipe,
    *,
    repo: RecipeRepository | None = None,
    index: RecipeSearchIndex | None = None,
    overwrite: bool = False,
) -> StoredRecipe:
    """Persist ``recipe`` to the repository and add it to the search index."""
    repo = repo or RecipeRepository()
    stored = repo.save(recipe, overwrite=overwrite)

    owns_index = index is None
    index = index or RecipeSearchIndex()
    try:
        index.upsert(recipe, slug=stored.slug, path=str(stored.directory))
    finally:
        if owns_index:
            index.close()
    return stored


def import_recipe_from_json(
    json_path: str | Path,
    *,
    repo: RecipeRepository | None = None,
    index: RecipeSearchIndex | None = None,
    overwrite: bool = False,
) -> StoredRecipe:
    """Load and validate a recipe from ``json_path`` then import it."""
    recipe = Recipe.model_validate_json(Path(json_path).read_text(encoding="utf-8"))
    return import_recipe(recipe, repo=repo, index=index, overwrite=overwrite)
