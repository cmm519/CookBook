from app.search import RecipeSearchIndex
from app.storage import RecipeRepository
from app.storage.repository import DuplicateRecipeError
from app.workflow.importer import import_recipe


def test_import_stores_package_and_indexes(tmp_path, sample_recipe):
    repo = RecipeRepository(root=tmp_path / "recipes")
    with RecipeSearchIndex(db_path=tmp_path / "recipes.db") as index:
        stored = import_recipe(sample_recipe, repo=repo, index=index)

        assert stored.recipe_json.exists()
        assert stored.recipe_md.exists()
        assert stored.metadata_json.exists()

        assert [r.slug for r in index.search("miso")] == [stored.slug]
        assert [r.slug for r in index.search("seafood")] == [stored.slug]
        assert index.search("nonexistent") == []


def test_duplicate_source_url_is_rejected(tmp_path, sample_recipe):
    repo = RecipeRepository(root=tmp_path / "recipes")
    with RecipeSearchIndex(db_path=tmp_path / "recipes.db") as index:
        import_recipe(sample_recipe, repo=repo, index=index)
        try:
            import_recipe(sample_recipe, repo=repo, index=index)
        except DuplicateRecipeError:
            pass
        else:  # pragma: no cover - failure path
            raise AssertionError("expected DuplicateRecipeError")


def test_load_round_trips(tmp_path, sample_recipe):
    repo = RecipeRepository(root=tmp_path / "recipes")
    with RecipeSearchIndex(db_path=tmp_path / "recipes.db") as index:
        stored = import_recipe(sample_recipe, repo=repo, index=index)
    loaded = repo.load(stored.slug)
    assert loaded.title == sample_recipe.title
    assert loaded.source_url == sample_recipe.source_url
