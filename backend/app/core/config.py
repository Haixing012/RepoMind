from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="github_helper", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_origin: str = Field(default="http://127.0.0.1:5173", alias="FRONTEND_ORIGIN")
    storage_root: Path = Field(default=Path("storage"), alias="STORAGE_ROOT")

    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    mysql_host: str = Field(default="47.119.20.247", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3308, alias="MYSQL_PORT")
    mysql_user: str = Field(default="github_helper", alias="MYSQL_USER")
    mysql_password: str = Field(default="pSN8t8ndSnjKzka5", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="github_helper", alias="MYSQL_DATABASE")

    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    analysis_max_files: int = Field(default=12, alias="ANALYSIS_MAX_FILES")
    analysis_max_bytes: int = Field(default=16000, alias="ANALYSIS_MAX_BYTES")

    @property
    def repo_storage(self) -> Path:
        return self.storage_root / "repos"

    @property
    def database_dsn(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    settings.repo_storage.mkdir(parents=True, exist_ok=True)
    return settings
