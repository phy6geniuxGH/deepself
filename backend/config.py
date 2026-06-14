from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App-wide config. Override any field via .env or env vars."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DEEPSELF_")

    # paths — base_dir = repo root (backend/config.py -> parent -> parent)
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    db_path: Path = data_dir / "deepself.db"
    pkm_dir: Path = data_dir / "pkm"

    # embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384  # all-MiniLM-L6-v2 output size

    # server
    host: str = "127.0.0.1"
    port: int = 8080
    # nicegui client-side storage signing key; override in .env for production
    storage_secret: str = "dev-deepself-change-me"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pkm_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
