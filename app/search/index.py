"""SQLite search index over stored recipes.

The filesystem package is the source of truth; this index makes recipes
searchable by title, ingredient name, tag, and source URL. The index can be
fully rebuilt from disk at any time.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from app.models import Recipe

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingredients (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tags (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    tag TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


@dataclass
class SearchResult:
    slug: str
    title: str
    source_url: str
    path: str


class RecipeSearchIndex:
    def __init__(self, db_path: str | Path = "recipes.db") -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def upsert(self, recipe: Recipe, slug: str, path: str | Path) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM recipes WHERE slug = ?", (slug,))
        cur.execute(
            "INSERT INTO recipes (slug, title, source_url, path) VALUES (?, ?, ?, ?)",
            (slug, recipe.title, recipe.source_url, str(path)),
        )
        recipe_id = cur.lastrowid
        cur.executemany(
            "INSERT INTO ingredients (recipe_id, name) VALUES (?, ?)",
            [(recipe_id, ing.item.lower()) for ing in recipe.ingredients],
        )
        cur.executemany(
            "INSERT INTO tags (recipe_id, tag) VALUES (?, ?)",
            [(recipe_id, tag.lower()) for tag in recipe.tags],
        )
        self._conn.commit()

    def search(self, query: str) -> list[SearchResult]:
        """Return recipes matching ``query`` in title, ingredient, or tag."""
        like = f"%{query.lower().strip()}%"
        rows = self._conn.execute(
            """
            SELECT DISTINCT r.slug, r.title, r.source_url, r.path
            FROM recipes r
            LEFT JOIN ingredients i ON i.recipe_id = r.id
            LEFT JOIN tags t ON t.recipe_id = r.id
            WHERE lower(r.title) LIKE ?
               OR i.name LIKE ?
               OR t.tag LIKE ?
            ORDER BY r.title
            """,
            (like, like, like),
        ).fetchall()
        return [
            SearchResult(slug=r["slug"], title=r["title"], source_url=r["source_url"], path=r["path"])
            for r in rows
        ]

    def all_recipes(self) -> list[SearchResult]:
        rows = self._conn.execute(
            "SELECT slug, title, source_url, path FROM recipes ORDER BY title"
        ).fetchall()
        return [
            SearchResult(slug=r["slug"], title=r["title"], source_url=r["source_url"], path=r["path"])
            for r in rows
        ]
