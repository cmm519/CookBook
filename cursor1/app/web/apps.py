"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.bugreport.debug_log import save_bug_report
from app.cli.import_cmd import run_import
from app.config import load_config
from app.shopping.list import build_shopping_list
from app.storage import PackageStorage
from app.search.sqlite_index import RecipeIndex
from app.workflow.factory import build_orchestrator
from app.steps.base import StepContext
import uuid

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _list_recipes(storage: PackageStorage, index: RecipeIndex) -> list[dict[str, str | None]]:
    return [
        {"slug": slug, **(index.get(slug) or {"title": slug, "source_url": "", "source_creator": None})}
        for slug in storage.list_slugs()
    ]


def _recipe_titles(storage: PackageStorage, index: RecipeIndex) -> list[dict[str, str]]:
    return [
        {
            "slug": slug,
            "title": (index.get(slug) or {}).get("title") or slug,
        }
        for slug in storage.list_slugs()
    ]


def create_production_app() -> FastAPI:
    app = FastAPI(title="CookBook")
    config = load_config()
    storage = PackageStorage(config.repository_path)
    index = RecipeIndex(config.database_path)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(
            request,
            "production/home.html",
            {"active_tab": "home"},
        )

    @app.get("/recipes", response_class=HTMLResponse)
    async def browse_recipes(request: Request, q: str = ""):
        recipes = index.search(q) if q else _list_recipes(storage, index)
        return templates.TemplateResponse(
            request,
            "production/browse.html",
            {"active_tab": "browse", "recipes": recipes, "query": q},
        )

    @app.post("/import")
    async def import_recipe(
        source_url: str = Form(...),
        user_comment: str = Form(""),
        custom_instruction: str = Form(""),
        video_processing: bool = Form(False),
    ):
        try:
            job, slug = run_import(
                source_url,
                user_comment=user_comment or None,
                custom_instruction=custom_instruction or None,
                video_processing_enabled=video_processing,
            )
            if slug:
                return RedirectResponse(url=f"/recipes/{slug}", status_code=303)
            return RedirectResponse(url="/", status_code=303)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/recipes/{slug}/video")
    async def recipe_video(slug: str):
        video_path = storage.package_dir(slug) / "video.mp4"
        if not video_path.is_file():
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(video_path, media_type="video/mp4")

    @app.get("/recipes/{slug}", response_class=HTMLResponse)
    async def recipe_detail(request: Request, slug: str):
        try:
            recipe = storage.read_recipe(slug)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Recipe not found") from exc
        has_video = (storage.package_dir(slug) / "video.mp4").is_file()
        return templates.TemplateResponse(
            request,
            "production/recipe.html",
            {"active_tab": "browse", "recipe": recipe, "slug": slug, "has_video": has_video},
        )

    @app.get("/recipes/{slug}/edit", response_class=HTMLResponse)
    async def recipe_edit_form(request: Request, slug: str):
        recipe = storage.read_recipe(slug)
        return templates.TemplateResponse(
            request,
            "production/edit.html",
            {"active_tab": "browse", "recipe": recipe, "slug": slug},
        )

    @app.post("/recipes/{slug}/edit")
    async def recipe_edit_submit(request: Request, slug: str):
        form = await request.form()
        recipe = storage.read_recipe(slug)
        updated = recipe.model_copy(update={
            "title": str(form.get("title", recipe.title)),
            "description": str(form.get("description", recipe.description or "")),
        })
        storage.update_recipe(slug, updated)
        from datetime import UTC, datetime
        index.upsert(slug, updated, updated_at=datetime.now(UTC).isoformat())
        return RedirectResponse(url=f"/recipes/{slug}", status_code=303)

    @app.post("/recipes/{slug}/rate")
    async def rate_recipe(slug: str, score: int = Form(...)):
        rating_path = storage.package_dir(slug) / "rating.json"
        from datetime import UTC, datetime
        import json
        rating_path.write_text(
            json.dumps({"score": score, "updated_at": datetime.now(UTC).isoformat()}) + "\n",
            encoding="utf-8",
        )
        return RedirectResponse(url=f"/recipes/{slug}", status_code=303)

    @app.get("/shopping", response_class=HTMLResponse)
    async def shopping_form(request: Request):
        recipes = _recipe_titles(storage, index)
        return templates.TemplateResponse(
            request,
            "production/shopping.html",
            {"active_tab": "shopping", "recipes": recipes, "items": []},
        )

    @app.post("/shopping", response_class=HTMLResponse)
    async def shopping_build(request: Request):
        form = await request.form()
        selected = [key.replace("slug_", "") for key in form if key.startswith("slug_")]
        items = build_shopping_list(storage, selected)
        return templates.TemplateResponse(
            request,
            "production/shopping.html",
            {
                "active_tab": "shopping",
                "recipes": _recipe_titles(storage, index),
                "items": items,
                "selected": selected,
            },
        )

    @app.post("/bug-report")
    async def bug_report(
        description: str = Form(...),
        related_recipe_slug: str = Form(""),
    ):
        config = load_config()
        report = save_bug_report(
            config.working_dir,
            description=description,
            debug_log_path=str(config.working_dir / "bugreports"),
            related_recipe_slug=related_recipe_slug or None,
        )
        return RedirectResponse(url="/", status_code=303)

    return app


def create_testing_app() -> FastAPI:
    app = FastAPI(title="CookBook Testing GUI")
    config = load_config()
    orchestrator = build_orchestrator(config)

    @app.get("/", response_class=HTMLResponse)
    async def testing_home(request: Request):
        urls_file = config.dataset_urls_file
        urls = []
        if urls_file.is_file():
            urls = [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        return templates.TemplateResponse(
            request,
            "testing/home.html",
            {"urls": urls, "results": []},
        )

    @app.post("/run-step/{step_number}", response_class=HTMLResponse)
    async def run_step(request: Request, step_number: int, source_url: str = Form(...)):
        job_id = f"test-{uuid.uuid4().hex[:8]}"
        working_dir = config.working_dir / job_id
        context = StepContext(
            job_id=job_id,
            source_url=source_url,
            working_dir=working_dir,
            repository_path=config.repository_path,
            dataset_raw_dir=config.dataset_raw_dir,
            video_processing_enabled=config.video_processing_default,
        )
        result = orchestrator.run_step(step_number, context)
        return templates.TemplateResponse(
            request,
            "testing/result.html",
            {"result": result, "context": context},
        )

    return app


def create_deployment_app() -> FastAPI:
    app = FastAPI(title="CookBook Deployment GUI")
    config = load_config()

    @app.get("/", response_class=HTMLResponse)
    async def deployment_home(request: Request):
        import shutil
        import subprocess

        docker_ok = shutil.which("docker") is not None
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        ollama_status = "unknown"
        try:
            import httpx
            r = httpx.get(f"{config.ollama_host}/api/tags", timeout=3.0)
            ollama_status = "ok" if r.status_code == 200 else "error"
        except Exception:
            ollama_status = "unreachable"

        return templates.TemplateResponse(
            request,
            "deployment/home.html",
            {
                "docker_ok": docker_ok,
                "ffmpeg_ok": ffmpeg_ok,
                "ollama_status": ollama_status,
                "formatter_model": config.formatter_model,
                "whisper_model": config.whisper_model,
            },
        )

    return app
