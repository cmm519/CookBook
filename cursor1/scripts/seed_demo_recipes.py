#!/usr/bin/env python3
"""Seed demo recipe packages from dataset manifest entries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.formatting.markdown import recipe_to_markdown
from app.models import Ingredient, Instruction, Recipe
from app.search.sqlite_index import RecipeIndex
from app.storage import PackageMetadata, PackageStorage

PLACEHOLDER_NOTE = "Demo recipe — re-import for full extraction."


def _parse_sectioned_caption(caption: str) -> tuple[list[str], list[str]] | None:
    """Parse INGREDIENTS / METHOD sections with bullet markers."""
    upper = caption.upper()
    ing_idx = upper.find("INGREDIENTS")
    method_idx = upper.find("METHOD")
    if ing_idx == -1 or method_idx == -1 or method_idx <= ing_idx:
        return None

    ing_block = caption[ing_idx:method_idx]
    method_block = caption[method_idx:]

    def extract_items(block: str) -> list[str]:
        items: list[str] = []
        for line in block.splitlines():
            line = line.strip()
            if not line or line.upper() in ("INGREDIENTS", "METHOD"):
                continue
            cleaned = re.sub(r"^[▪️•\-\*]\s*", "", line)
            cleaned = re.sub(r"^[\d]+[\.\)]\s*", "", cleaned)
            if cleaned and not cleaned.startswith("#"):
                items.append(cleaned)
        return items

    ingredients = extract_items(ing_block)
    instructions = extract_items(method_block)
    if len(ingredients) < 1 or len(instructions) < 1:
        return None
    return ingredients, instructions


def _parse_prose_caption(caption: str) -> tuple[list[str], list[str]] | None:
    """Parse home_chef_harmony-style caption with ingredients: and prose method."""
    lower = caption.lower()
    ing_idx = lower.find("ingredients:")
    if ing_idx == -1:
        return None

    body = caption[ing_idx + len("ingredients:"):]
    hash_idx = body.find("#")
    if hash_idx != -1:
        body = body[:hash_idx]

    sentences = [s.strip() for s in re.split(r"(?<=[.!])\s+", body) if s.strip()]
    method_start = None
    for i, sentence in enumerate(sentences):
        if re.match(r"^(cut|heat|add|bake|mix|stir|season|use)\b", sentence, re.I):
            method_start = i
            break

    if method_start is None:
        return None

    ing_text = " ".join(sentences[:method_start])
    ing_parts = [p.strip().rstrip(",") for p in re.split(r",\s*", ing_text) if p.strip()]
    ingredients = [p for p in ing_parts if len(p) > 2]

    instructions = sentences[method_start:]
    if len(ingredients) < 1 or len(instructions) < 1:
        return None
    return ingredients, instructions


def _build_from_lists(
    title: str,
    source_url: str,
    author: str | None,
    ingredient_lines: list[str],
    instruction_lines: list[str],
    *,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Recipe:
    return Recipe(
        title=title,
        description=description,
        ingredients=[Ingredient(item=line) for line in ingredient_lines],
        instructions=[
            Instruction(step=i, text=text) for i, text in enumerate(instruction_lines, start=1)
        ],
        tags=tags or ["demo"],
        source_url=source_url,
        source_creator=author,
    )


def _placeholder_recipe(
    title: str,
    source_url: str,
    author: str | None,
    description: str,
    *,
    tags: list[str] | None = None,
) -> Recipe:
    return Recipe(
        title=title,
        description=description,
        ingredients=[
            Ingredient(item="Ingredients from original Reel"),
            Ingredient(item="See video for quantities"),
        ],
        instructions=[
            Instruction(step=1, text="Watch the embedded video for preparation steps."),
            Instruction(step=2, text=PLACEHOLDER_NOTE),
        ],
        notes=[PLACEHOLDER_NOTE],
        tags=tags or ["demo", "placeholder"],
        source_url=source_url,
        source_creator=author,
    )


def recipe_for_entry(entry: dict) -> Recipe:
    reel_id = entry["id"]
    source_url = entry["source_url"]
    author = entry.get("author") or entry.get("author_username")
    caption = entry.get("caption", "")

    if reel_id == "DaBU4FutkT0":
        parsed = _parse_sectioned_caption(caption)
        if parsed:
            ing, steps = parsed
            return _build_from_lists(
                "Courgette Tomato Pasta",
                source_url,
                author,
                ing,
                steps,
                description="A super easy and delicious midweek pasta from @doctorbowl.",
                tags=["demo", "pasta", "healthy"],
            )

    if reel_id == "DUw9puDERf1":
        parsed = _parse_prose_caption(caption)
        if parsed:
            ing, steps = parsed
            return _build_from_lists(
                "Stuffed Pancake Chicken Bake",
                source_url,
                author,
                ing,
                steps,
                description="Layered pancake bake with chicken, peppers, and cheese.",
                tags=["demo", "chicken", "bake"],
            )

    placeholders: dict[str, tuple[str, str, list[str]]] = {
        "DaF766uDQ0C": (
            "High Protein Meal",
            "Made with heart — a rich, cheesy high-protein dish.",
            ["demo", "high-protein"],
        ),
        "DWGObcgEVM7": (
            "Maggi Omelet",
            "Classic Maggi omelet recipe from @rakhirannaghor.",
            ["demo", "omelet"],
        ),
        "DNaXvZzBpum": (
            "5-Minute Kitchen Hack",
            "Quick kitchen tip from @5minute.recipes.official.",
            ["demo", "quick"],
        ),
        "DaOEpIAk2Pe": (
            "Juicy Center Protein Bowl",
            "High-protein bowl with a juicy, cheesy center.",
            ["demo", "high-protein"],
        ),
    }

    if reel_id in placeholders:
        title, desc, tags = placeholders[reel_id]
        first_line = caption.split("\n")[0].strip() if caption else desc
        return _placeholder_recipe(title, source_url, author, first_line or desc, tags=tags)

    return _placeholder_recipe(
        entry.get("title", reel_id),
        source_url,
        author,
        caption.split("\n")[0] if caption else "Demo recipe",
    )


def seed(*, repo_path: Path, db_path: Path, dataset_dir: Path, force: bool = False) -> int:
    manifest_path = dataset_dir / "manifest.json"
    raw_dir = dataset_dir / "raw"
    transcripts_dir = dataset_dir / "transcripts"

    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    storage = PackageStorage(repo_path)
    index = RecipeIndex(db_path)
    created = 0
    skipped = 0

    for entry in manifest.get("entries", []):
        reel_id = entry["id"]
        video_src = raw_dir / f"{reel_id}.mp4"
        if not video_src.is_file():
            print(f"  skip {reel_id}: no video at {video_src}")
            skipped += 1
            continue

        recipe = recipe_for_entry(entry)
        slug = storage.unique_slug(recipe.title, source_url=entry["source_url"])

        if storage.package_dir(slug).exists() and not force:
            print(f"  skip {slug}: already exists (use --force to overwrite)")
            skipped += 1
            continue

        transcript_txt = None
        transcript_path = transcripts_dir / f"{reel_id}.txt"
        if transcript_path.is_file():
            transcript_txt = transcript_path.read_text(encoding="utf-8")

        metadata = PackageMetadata(
            source_url=entry["source_url"],
            source_creator=entry.get("author"),
            date_added=datetime.now(UTC).isoformat(),
            slug=slug,
        )

        storage.write_package(
            slug,
            recipe=recipe,
            recipe_md=recipe_to_markdown(recipe),
            metadata=metadata,
            video_path=video_src,
            transcript_txt=transcript_txt,
        )
        index.upsert(slug, recipe, updated_at=datetime.now(UTC).isoformat())
        print(f"  created {slug} ({recipe.title})")
        created += 1

    print(f"\nDone: {created} created, {skipped} skipped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo recipes from dataset manifest")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT / "recipes")
    parser.add_argument("--db", type=Path, default=REPO_ROOT / "data" / "db" / "recipes.db")
    parser.add_argument("--dataset", type=Path, default=REPO_ROOT / "dataset")
    parser.add_argument("--force", action="store_true", help="Overwrite existing packages")
    args = parser.parse_args()

    args.repo.mkdir(parents=True, exist_ok=True)
    args.db.parent.mkdir(parents=True, exist_ok=True)

    print(f"Seeding recipes into {args.repo}")
    return seed(
        repo_path=args.repo,
        db_path=args.db,
        dataset_dir=args.dataset,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
