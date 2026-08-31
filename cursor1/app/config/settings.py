"""Environment-backed configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CookBookConfig(BaseSettings):
    """Application configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mode: str = Field(default="test", alias="MODE")
    repository_path: Path = Field(default=Path("/data/recipes"), alias="REPOSITORY_PATH")
    working_dir: Path = Field(default=Path("/data/working"), alias="WORKING_DIR")
    database_path: Path = Field(default=Path("/data/db/recipes.db"), alias="DATABASE_PATH")
    dataset_dir: Path = Field(default=Path("/data/dataset"), alias="DATASET_DIR")
    dataset_raw_dir: Path = Field(default=Path("/data/dataset/raw"), alias="DATASET_RAW_DIR")
    dataset_manifest_path: Path = Field(
        default=Path("/data/dataset/manifest.json"),
        alias="DATASET_MANIFEST_PATH",
    )
    dataset_metadata_dir: Path = Field(
        default=Path("/data/dataset/metadata"),
        alias="DATASET_METADATA_DIR",
    )
    save_metadata: bool = Field(default=True, alias="SAVE_METADATA")
    download_limit: int = Field(default=50, alias="DOWNLOAD_LIMIT", ge=1, le=50)
    download_source_url: str | None = Field(default=None, alias="DOWNLOAD_SOURCE_URL")
    dataset_urls_file: Path = Field(
        default=Path("/data/dataset/urls.txt"),
        alias="DATASET_URLS_FILE",
    )
    ytdlp_cookies_file: Path | None = Field(default=None, alias="YTDLP_COOKIES_FILE")
    ytdlp_cookies_from_browser: str | None = Field(
        default=None,
        alias="YTDLP_COOKIES_FROM_BROWSER",
    )
    whisper_model: str = Field(default="large-v3", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="cuda", alias="WHISPER_DEVICE")
    formatter_provider: str = Field(default="ollama", alias="FORMATTER_PROVIDER")
    ollama_host: str = Field(default="http://ollama:11434", alias="OLLAMA_HOST")
    formatter_model: str = Field(default="qwen2.5:7b-instruct", alias="FORMATTER_MODEL")
    frame_interval: float = Field(default=2.0, alias="FRAME_INTERVAL")
    keep_working: bool = Field(default=False, alias="KEEP_WORKING")
    video_processing_default: bool = Field(default=True, alias="VIDEO_PROCESSING_DEFAULT")
    web_port: int = Field(default=8080, alias="WEB_PORT")
    testing_gui_port: int = Field(default=8081, alias="TESTING_GUI_PORT")
    deployment_gui_port: int = Field(default=8082, alias="DEPLOYMENT_GUI_PORT")


@lru_cache
def load_config() -> CookBookConfig:
    """Load and cache configuration."""
    return CookBookConfig()
