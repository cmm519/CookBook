"""Smoke tests for configuration loading."""

from pathlib import Path

from app.config import CookBookConfig, load_config


def test_load_config_defaults():
    config = CookBookConfig(_env_file=None)
    assert config.repository_path == Path("/data/recipes")
    assert config.working_dir == Path("/data/working")
    assert config.database_path == Path("/data/db/recipes.db")
    assert config.dataset_dir == Path("/data/dataset")
    assert config.dataset_raw_dir == Path("/data/dataset/raw")
    assert config.download_limit == 50
    assert config.whisper_model == "large-v3"
    assert config.ollama_host == "http://ollama:11434"


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("REPOSITORY_PATH", "/custom/recipes")
    monkeypatch.setenv("DOWNLOAD_LIMIT", "10")
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")

    config = CookBookConfig(_env_file=None)
    assert config.repository_path == Path("/custom/recipes")
    assert config.download_limit == 10
    assert config.whisper_device == "cpu"
