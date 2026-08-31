"""Recipe package filesystem storage."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pydantic import BaseModel

from app.models import Recipe


class PackageMetadata(BaseModel):
    source_url: str
    source_creator: str | None = None
    date_added: str
    pipeline_version: str = "0.1.0"
    slug: str


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or "recipe"


class PackageStorage:
    """Read/write recipe packages under recipes/<slug>/."""

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = Path(repository_path)
        self.repository_path.mkdir(parents=True, exist_ok=True)

    def package_dir(self, slug: str) -> Path:
        return self.repository_path / slug

    def unique_slug(self, title: str, *, source_url: str | None = None) -> str:
        base = slugify(title)
        candidate = base
        index = 2
        while self.package_dir(candidate).exists():
            if source_url:
                meta_path = self.package_dir(candidate) / "metadata.json"
                if meta_path.is_file():
                    data = json.loads(meta_path.read_text(encoding="utf-8"))
                    if data.get("source_url") == source_url:
                        return candidate
            candidate = f"{base}-{index}"
            index += 1
        return candidate

    def write_package(
        self,
        slug: str,
        *,
        recipe: Recipe,
        recipe_md: str,
        metadata: PackageMetadata,
        video_path: Path | None = None,
        transcript_txt: str | None = None,
        transcript_json: dict | None = None,
        vision_json: dict | None = None,
    ) -> Path:
        package_dir = self.package_dir(slug)
        package_dir.mkdir(parents=True, exist_ok=True)

        (package_dir / "recipe.json").write_text(
            recipe.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (package_dir / "recipe.md").write_text(recipe_md, encoding="utf-8")
        (package_dir / "metadata.json").write_text(
            metadata.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

        if transcript_txt is not None:
            (package_dir / "transcript.txt").write_text(transcript_txt, encoding="utf-8")
        if transcript_json is not None:
            (package_dir / "transcript.json").write_text(
                json.dumps(transcript_json, indent=2) + "\n",
                encoding="utf-8",
            )
        if vision_json is not None:
            (package_dir / "vision.json").write_text(
                json.dumps(vision_json, indent=2) + "\n",
                encoding="utf-8",
            )
        if video_path and video_path.is_file():
            dest = package_dir / "video.mp4"
            if video_path.resolve() != dest.resolve():
                shutil.copy2(video_path, dest)

        return package_dir

    def read_recipe(self, slug: str) -> Recipe:
        path = self.package_dir(slug) / "recipe.json"
        return Recipe.model_validate_json(path.read_text(encoding="utf-8"))

    def list_slugs(self) -> list[str]:
        if not self.repository_path.is_dir():
            return []
        return sorted(
            item.name
            for item in self.repository_path.iterdir()
            if item.is_dir() and (item / "recipe.json").is_file()
        )

    def update_recipe(self, slug: str, recipe: Recipe) -> None:
        path = self.package_dir(slug) / "recipe.json"
        path.write_text(recipe.model_dump_json(indent=2) + "\n", encoding="utf-8")
