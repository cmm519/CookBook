"""Step 8: Normalize and render Markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.formatting.markdown import normalize_recipe, recipe_to_markdown
from app.models import Recipe
from app.steps.base import PipelineStep, StepPrerequisiteError


class NormalizeMarkdownStep(PipelineStep):
    name = "normalize_markdown"
    step_number = 8
    requires = [7]

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        recipe_data = context.artifact("recipe")
        if not recipe_data:
            draft = context.artifact("recipe_draft_path")
            if not draft or not Path(draft).is_file():
                raise StepPrerequisiteError("recipe draft missing from step 7")
            recipe_data = json.loads(Path(draft).read_text(encoding="utf-8"))
        recipe = normalize_recipe(Recipe.model_validate(recipe_data))
        markdown = recipe_to_markdown(recipe)
        md_path = context.working_dir / "recipe.md"
        json_path = context.working_dir / "recipe.json"
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(recipe.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return {
            "recipe_path": str(json_path),
            "recipe_md_path": str(md_path),
            "recipe": recipe.model_dump(mode="json"),
            "recipe_md": markdown,
        }, {}
