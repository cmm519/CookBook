"""Persist a complete recipe package to disk, one directory per recipe.

The filesystem is the source of truth. Each recipe is stored under
``recipes/<slug>/`` with the canonical ``recipe.json``, rendered ``recipe.md``,
and ``metadata.json``. Duplicate detection is by source URL first.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.formatting import render_markdown
from app.models import Recipe, RecipeMetadata
from app.storage.slug import slugify


@dataclass
class StoredRecipe:
    slug: str
    directory: Path
    recipe_json: Path
    recipe_md: Path
    metadata_json: Path


class DuplicateRecipeError(Exception):
    """Raised when a recipe with the same source URL already exists."""


class RecipeRepository:
    def __init__(self, root: str | Path = "recipes") -> None:
        self.root = Path(root)

    def _unique_dir(self, slug: str) -> Path:
        candidate = self.root / slug
        suffix = 2
        while candidate.exists():
            candidate = self.root / f"{slug}-{suffix}"
            suffix += 1
        return candidate

    def find_by_source_url(self, source_url: str) -> Path | None:
        if not self.root.exists():
            return None
        for meta_path in sorted(self.root.glob("*/metadata.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("source_url") == source_url:
                return meta_path.parent
        return None

    def save(self, recipe: Recipe, *, overwrite: bool = False) -> StoredRecipe:
        existing = self.find_by_source_url(recipe.source_url)
        if existing is not None and not overwrite:
            raise DuplicateRecipeError(
                f"A recipe from {recipe.source_url} already exists at {existing}"
            )

        directory = existing if (existing and overwrite) else self._unique_dir(slugify(recipe.title))
        directory.mkdir(parents=True, exist_ok=True)

        recipe_json = directory / "recipe.json"
        recipe_md = directory / "recipe.md"
        metadata_json = directory / "metadata.json"

        recipe_json.write_text(
            recipe.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8"
        )
        recipe_md.write_text(render_markdown(recipe), encoding="utf-8")

        metadata = RecipeMetadata(
            source_url=recipe.source_url,
            creator=recipe.source_creator,
            title_original=recipe.title,
            date_added=datetime.now(UTC).isoformat(),
        )
        metadata_json.write_text(
            metadata.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        return StoredRecipe(
            slug=directory.name,
            directory=directory,
            recipe_json=recipe_json,
            recipe_md=recipe_md,
            metadata_json=metadata_json,
        )

    def load(self, slug: str) -> Recipe:
        recipe_json = self.root / slug / "recipe.json"
        if not recipe_json.exists():
            raise FileNotFoundError(f"No recipe found for slug {slug!r}")
        return Recipe.model_validate_json(recipe_json.read_text(encoding="utf-8"))
