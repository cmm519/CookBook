"""Deterministic Markdown rendering."""

from __future__ import annotations

from app.models import Recipe


def recipe_to_markdown(recipe: Recipe) -> str:
    lines: list[str] = [f"# {recipe.title}", ""]
    if recipe.description:
        lines.extend([recipe.description, ""])
    meta_parts = []
    if recipe.servings:
        meta_parts.append(f"**Servings:** {recipe.servings}")
    if recipe.prep_time:
        meta_parts.append(f"**Prep:** {recipe.prep_time}")
    if recipe.cook_time:
        meta_parts.append(f"**Cook:** {recipe.cook_time}")
    if recipe.total_time:
        meta_parts.append(f"**Total:** {recipe.total_time}")
    if meta_parts:
        lines.extend([" | ".join(meta_parts), ""])

    lines.extend(["## Ingredients", ""])
    for ingredient in recipe.ingredients:
        parts = []
        if ingredient.quantity:
            parts.append(ingredient.quantity)
        parts.append(ingredient.item)
        if ingredient.preparation:
            parts.append(f"({ingredient.preparation})")
        line = " ".join(parts)
        if ingredient.notes:
            line += f" — {ingredient.notes}"
        lines.append(f"- {line}")

    lines.extend(["", "## Instructions", ""])
    for instruction in recipe.instructions:
        extra = []
        if instruction.duration:
            extra.append(instruction.duration)
        if instruction.temperature:
            extra.append(instruction.temperature)
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"{instruction.step}. {instruction.text}{suffix}")

    if recipe.notes:
        lines.extend(["", "## Notes", ""])
        for note in recipe.notes:
            lines.append(f"- {note}")

    if recipe.tags:
        lines.extend(["", f"**Tags:** {', '.join(recipe.tags)}"])

    if recipe.source_url:
        lines.extend(["", f"**Source:** {recipe.source_url}"])

    return "\n".join(lines) + "\n"


def normalize_recipe(recipe: Recipe) -> Recipe:
    """Ensure instruction steps are sequential."""
    normalized_instructions = [
        instruction.model_copy(update={"step": index})
        for index, instruction in enumerate(recipe.instructions, start=1)
    ]
    return recipe.model_copy(update={"instructions": normalized_instructions})
