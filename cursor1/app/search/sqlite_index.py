"""SQLite recipe search index."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import Recipe


class RecipeIndex:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    slug TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_creator TEXT,
                    ingredients_text TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title)"
            )
            conn.commit()

    def upsert(self, slug: str, recipe: Recipe, *, updated_at: str) -> None:
        ingredients_text = " ".join(
            f"{ing.quantity or ''} {ing.item}".strip() for ing in recipe.ingredients
        )
        body_text = " ".join(step.text for step in recipe.instructions)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO recipes (slug, title, source_url, source_creator, ingredients_text, body_text, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title=excluded.title,
                    source_url=excluded.source_url,
                    source_creator=excluded.source_creator,
                    ingredients_text=excluded.ingredients_text,
                    body_text=excluded.body_text,
                    updated_at=excluded.updated_at
                """,
                (
                    slug,
                    recipe.title,
                    recipe.source_url,
                    recipe.source_creator,
                    ingredients_text,
                    body_text,
                    updated_at,
                ),
            )
            conn.commit()

    def search(self, query: str, *, limit: int = 50) -> list[dict[str, str]]:
        pattern = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT slug, title, source_url, source_creator
                FROM recipes
                WHERE title LIKE ? OR ingredients_text LIKE ? OR body_text LIKE ?
                ORDER BY title
                LIMIT ?
                """,
                (pattern, pattern, pattern, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, slug: str) -> dict[str, str] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT slug, title, source_url, source_creator FROM recipes WHERE slug = ?",
                (slug,),
            ).fetchone()
        return dict(row) if row else None

    def delete(self, slug: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM recipes WHERE slug = ?", (slug,))
            conn.commit()
