"""SQLite-backed search index over stored recipes."""

from app.search.index import RecipeSearchIndex, SearchResult

__all__ = ["RecipeSearchIndex", "SearchResult"]
