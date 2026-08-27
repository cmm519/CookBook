"""Command-line interface for the CookBook recipe repository.

Commands:

- ``cookbook import-json <file>``  import a validated recipe JSON file
- ``cookbook search <query>``      search indexed recipes
- ``cookbook show <slug>``         print a stored recipe's Markdown
- ``cookbook demo``                run an offline end-to-end demo
- ``cookbook version``             print the package version
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from app import __version__
from app.formatting import render_markdown
from app.models import Ingredient, Instruction, Recipe
from app.search import RecipeSearchIndex
from app.storage import RecipeRepository
from app.storage.repository import DuplicateRecipeError
from app.workflow.importer import import_recipe, import_recipe_from_json

app = typer.Typer(
    add_completion=False,
    help="Local-first recipe repository: import, search, and view recipes.",
)


def _default_repo() -> RecipeRepository:
    return RecipeRepository()


@app.command()
def version() -> None:
    """Print the CookBook version."""
    typer.echo(__version__)


@app.command("import-json")
def import_json(
    path: Annotated[
        Path, typer.Argument(exists=True, readable=True, help="Path to a recipe JSON file.")
    ],
    overwrite: Annotated[
        bool, typer.Option("--overwrite", help="Overwrite an existing recipe with the same source URL.")
    ] = False,
) -> None:
    """Import a validated recipe JSON file into the repository and index."""
    try:
        stored = import_recipe_from_json(path, overwrite=overwrite)
    except DuplicateRecipeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.secho(f"Imported recipe -> {stored.directory}", fg=typer.colors.GREEN)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Text to match in title, ingredient, or tag.")],
) -> None:
    """Search indexed recipes."""
    with RecipeSearchIndex() as index:
        results = index.search(query)
    if not results:
        typer.echo(f"No recipes matched {query!r}.")
        raise typer.Exit(code=0)
    for res in results:
        typer.echo(f"{res.slug}\t{res.title}\t{res.source_url}")


@app.command()
def show(
    slug: Annotated[str, typer.Argument(help="Recipe slug (directory name).")],
) -> None:
    """Print a stored recipe's rendered Markdown."""
    repo = _default_repo()
    try:
        recipe = repo.load(slug)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(render_markdown(recipe))


@app.command()
def demo() -> None:
    """Run an offline end-to-end demo: build, store, index, and search a recipe."""
    recipe = Recipe(
        title="Chicken Teriyaki",
        description="A quick weeknight teriyaki with a glossy pan sauce.",
        servings="2 servings",
        prep_time="10 min",
        cook_time="15 min",
        total_time="25 min",
        ingredients=[
            Ingredient(item="chicken thighs", quantity="1 lb", preparation="cut into bite-size pieces"),
            Ingredient(item="soy sauce", quantity="3 tbsp"),
            Ingredient(item="mirin", quantity="2 tbsp"),
            Ingredient(item="brown sugar", quantity="1 tbsp"),
            Ingredient(item="garlic", quantity="2 cloves", preparation="minced"),
            Ingredient(item="ginger", quantity="1 tsp", preparation="grated"),
        ],
        instructions=[
            Instruction(step=1, text="Sear the chicken over medium-high heat until browned.", duration="6 min"),
            Instruction(step=2, text="Add soy sauce, mirin, sugar, garlic, and ginger."),
            Instruction(step=3, text="Simmer until the sauce thickens and coats the chicken.", duration="5 min"),
        ],
        notes=["Serve over steamed rice with sesame seeds."],
        tags=["asian", "chicken", "quick"],
        source_url="https://www.instagram.com/reel/DEMO12345/",
        source_creator="cookbook-demo",
    )

    repo = RecipeRepository()
    with RecipeSearchIndex() as index:
        stored = import_recipe(recipe, repo=repo, index=index, overwrite=True)
        typer.secho(f"Stored recipe package at {stored.directory}", fg=typer.colors.GREEN)
        typer.echo(f"  - {stored.recipe_json.name}")
        typer.echo(f"  - {stored.recipe_md.name}")
        typer.echo(f"  - {stored.metadata_json.name}")

        typer.echo("\nSearch results for 'chicken':")
        for res in index.search("chicken"):
            typer.echo(f"  {res.slug}\t{res.title}")

    typer.echo("\nRendered Markdown:\n")
    typer.echo(render_markdown(recipe))


if __name__ == "__main__":  # pragma: no cover
    app()
