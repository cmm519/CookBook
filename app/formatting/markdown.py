"""Render a validated :class:`~app.models.Recipe` into cookbook Markdown.

The formatter is intentionally deterministic (no LLM): the same recipe always
produces the same Markdown. Optional fields are omitted rather than rendered as
empty placeholders.
"""

from __future__ import annotations

from app.models import Ingredient, Recipe


def _format_ingredient(ing: Ingredient) -> str:
    parts: list[str] = []
    if ing.quantity:
        parts.append(ing.quantity.strip())
    item = ing.item.strip()
    if ing.preparation:
        item = f"{item}, {ing.preparation.strip()}"
    parts.append(item)
    line = " ".join(parts)
    if ing.notes:
        line = f"{line} ({ing.notes.strip()})"
    return line


def render_markdown(recipe: Recipe) -> str:
    """Return a Markdown document for ``recipe``."""
    lines: list[str] = [f"# {recipe.title.strip()}", ""]

    if recipe.description:
        lines += [recipe.description.strip(), ""]

    if recipe.servings:
        lines += ["## Yield", recipe.servings.strip(), ""]

    time_bits: list[str] = []
    if recipe.prep_time:
        time_bits.append(f"- Prep: {recipe.prep_time.strip()}")
    if recipe.cook_time:
        time_bits.append(f"- Cook: {recipe.cook_time.strip()}")
    if recipe.total_time:
        time_bits.append(f"- Total: {recipe.total_time.strip()}")
    if time_bits:
        lines += ["## Time", *time_bits, ""]

    if recipe.ingredients:
        lines.append("## Ingredients")
        lines += [f"- {_format_ingredient(ing)}" for ing in recipe.ingredients]
        lines.append("")

    if recipe.instructions:
        lines.append("## Instructions")
        ordered = sorted(recipe.instructions, key=lambda i: i.step)
        for idx, instr in enumerate(ordered, start=1):
            suffix_bits: list[str] = []
            if instr.duration:
                suffix_bits.append(instr.duration.strip())
            if instr.temperature:
                suffix_bits.append(instr.temperature.strip())
            suffix = f" _({', '.join(suffix_bits)})_" if suffix_bits else ""
            lines.append(f"{idx}. {instr.text.strip()}{suffix}")
        lines.append("")

    if recipe.notes:
        lines.append("## Notes")
        lines += [f"- {note.strip()}" for note in recipe.notes]
        lines.append("")

    if recipe.tags:
        lines += ["## Tags", ", ".join(tag.strip() for tag in recipe.tags), ""]

    lines += ["## Source", f"[Original Video]({recipe.source_url})"]
    if recipe.source_creator:
        lines.append(f"By {recipe.source_creator.strip()}")

    return "\n".join(lines).rstrip() + "\n"
