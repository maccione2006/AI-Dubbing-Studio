from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _as_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_name: str = "AI Dubbing Studio"
    environment: str = "development"
    data_dir: Path = Path("data")
    temp_dir: Path = Path("tmp")
    model_cache_dir: Path = Path("models")
    log_level: str = "INFO"
    debug: bool = False
    use_vegas_integration: bool = False
    vegas_exe_path: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "AI Dubbing Studio"),
            environment=os.getenv("ENVIRONMENT", "development"),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            temp_dir=Path(os.getenv("TEMP_DIR", "tmp")),
            model_cache_dir=Path(os.getenv("MODEL_CACHE_DIR", "models")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            debug=_as_bool(os.getenv("DEBUG"), False),
            use_vegas_integration=_as_bool(os.getenv("USE_VEGAS_INTEGRATION"), False),
            vegas_exe_path=os.getenv("VEGAS_EXE_PATH", "").strip(),
        )


def get_settings() -> Settings:
    return Settings.from_env()
