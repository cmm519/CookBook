"""Step 7: Format recipe via LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.extraction.formatter_provider import FormatterProvider
from app.extraction.ollama_formatter import safe_format
from app.models import ConsolidatedSourceInput
from app.steps.base import PipelineStep, StepPrerequisiteError


class FormatRecipeStep(PipelineStep):
    name = "format_recipe"
    step_number = 7
    requires = [6]

    def __init__(self, provider: FormatterProvider) -> None:
        self._provider = provider

    def execute(self, context) -> tuple[dict[str, Any], dict[str, Any]]:
        consolidated_data = context.artifact("consolidated")
        if not consolidated_data:
            path = context.artifact("consolidated_path")
            if not path or not Path(path).is_file():
                raise StepPrerequisiteError("consolidated input missing from step 6")
            consolidated_data = json.loads(Path(path).read_text(encoding="utf-8"))
        consolidated = ConsolidatedSourceInput.model_validate(consolidated_data)
        recipe = safe_format(self._provider, consolidated)
        draft_path = context.working_dir / "recipe.draft.json"
        draft_path.write_text(recipe.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return {
            "recipe_draft_path": str(draft_path),
            "recipe": recipe.model_dump(mode="json"),
        }, {"ingredient_count": len(recipe.ingredients)}
