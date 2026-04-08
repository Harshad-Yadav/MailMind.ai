from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_name: str = "Advanced Email Triage OpenEnv"
    api_prefix: str = "/api"
    environment_name: str = "advanced-email-triage"
    model_backend: str = Field(default="heuristic", description="heuristic|classical|transformer")
    dataset_path: Path = Path("dataset/emails.csv")
    sqlite_path: Path = Path("dataset/email_triage.db")
    metrics_path: Path = Path("models/metrics.json")
    model_registry_path: Path = Path("models/registry.json")
    ui_dist_path: Path = Path("ui/dist")
    default_seed: int = 42
    sample_size: int = 5000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        project_name=os.getenv("PROJECT_NAME", "Advanced Email Triage OpenEnv"),
        api_prefix=os.getenv("API_PREFIX", "/api"),
        environment_name=os.getenv("ENVIRONMENT_NAME", "advanced-email-triage"),
        model_backend=os.getenv("MODEL_BACKEND", "heuristic"),
        dataset_path=Path(os.getenv("DATASET_PATH", "dataset/emails.csv")),
        sqlite_path=Path(os.getenv("SQLITE_PATH", "dataset/email_triage.db")),
        metrics_path=Path(os.getenv("METRICS_PATH", "models/metrics.json")),
        model_registry_path=Path(os.getenv("MODEL_REGISTRY_PATH", "models/registry.json")),
        ui_dist_path=Path(os.getenv("UI_DIST_PATH", "ui/dist")),
        default_seed=int(os.getenv("DEFAULT_SEED", "42")),
        sample_size=int(os.getenv("SAMPLE_SIZE", "5000")),
        cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"),
    )
