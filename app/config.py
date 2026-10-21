from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Elf Studio API"
    api_prefix: str = "/api/v1"

    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'elf_studio.db').as_posix()}"
    auth_secret_key: str = "dev-only-change-me-before-deploying"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    cors_origin_regex: str = r"^http://(localhost|127\.0\.0\.1):\d+$"

    admin_username: str = "demo"
    admin_password: str = "demo1234"
    admin_display_name: str = "研究员"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
