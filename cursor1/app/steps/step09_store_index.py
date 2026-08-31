"""Step 9: Store recipe package and index."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import CookBookConfig
from app.models import Recipe
from app.search.sqlite_index import RecipeIndex
from app.steps.base import PipelineStep, StepPrerequisiteError
from app.storage import PackageMetadata, PackageStorage


class StoreIndexStep(PipelineStep):
    name = "store_index"
    step_number = 9
    requires = [8]

    def __init__(self, config: CookBookConfig) -> None:
        self._config = config

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        recipe_data = context.artifact("recipe")
        recipe_md = context.artifact("recipe_md")
        if not recipe_data or not recipe_md:
            raise StepPrerequisiteError("normalized recipe missing from step 8")
        recipe = Recipe.model_validate(recipe_data)
        storage = PackageStorage(self._config.repository_path)
        slug = storage.unique_slug(recipe.title, source_url=recipe.source_url)
        now = datetime.now(UTC).isoformat()
        metadata = PackageMetadata(
            source_url=recipe.source_url,
            source_creator=recipe.source_creator,
            date_added=now,
            slug=slug,
        )
        transcript_txt = None
        transcript_json = None
        transcript_path = context.artifact("transcript_path")
        if transcript_path and Path(transcript_path).is_file():
            transcript_txt = Path(transcript_path).read_text(encoding="utf-8")
        transcript_json_path = context.artifact("transcript_json_path")
        if transcript_json_path and Path(transcript_json_path).is_file():
            transcript_json = json.loads(Path(transcript_json_path).read_text(encoding="utf-8"))
        vision_json = context.artifact("vision")
        video_path = context.artifact("video_path")
        package_dir = storage.write_package(
            slug,
            recipe=recipe,
            recipe_md=recipe_md,
            metadata=metadata,
            video_path=Path(video_path) if video_path else None,
            transcript_txt=transcript_txt,
            transcript_json=transcript_json,
            vision_json=vision_json if vision_json else None,
        )
        index = RecipeIndex(self._config.database_path)
        index.upsert(slug, recipe, updated_at=now)
        return {
            "slug": slug,
            "package_dir": str(package_dir),
        }, {"slug": slug}
