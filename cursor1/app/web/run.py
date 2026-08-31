"""Uvicorn entrypoints for web GUIs."""

from __future__ import annotations

import uvicorn

from app.config import load_config
from app.web.apps import create_deployment_app, create_production_app, create_testing_app


def run_production() -> None:
    config = load_config()
    uvicorn.run(create_production_app(), host="0.0.0.0", port=config.web_port)


def run_testing_gui() -> None:
    config = load_config()
    uvicorn.run(create_testing_app(), host="0.0.0.0", port=config.testing_gui_port)


def run_deployment_gui() -> None:
    config = load_config()
    uvicorn.run(create_deployment_app(), host="0.0.0.0", port=config.deployment_gui_port)
