import os
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Settings:
    """Simple configuration without Pydantic dependency."""
    app_name: str = "Climate API"
    api_v1_prefix: str = "/api/v1"
    default_start_year: int = 1990
    default_end_year: int = 2020
    model_dir: Path = Path("data/models")
    model_filename: str = "climate_full.bin"  # full size (~400MB) expected
    sample_model_filename: str = "climate_sample.bin"  # tiny test model (~1MB)
    use_sample_model: bool = False  # toggle for tests/dev

    @property
    def active_model_path(self) -> Path:
        name = self.sample_model_filename if self.use_sample_model else self.model_filename
        return self.model_dir / name

    @classmethod
    def from_env(cls) -> 'Settings':
        """Load settings from environment variables."""
        return cls(
            app_name=os.getenv("APP_NAME", "Climate API"),
            api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
            default_start_year=int(os.getenv("DEFAULT_START_YEAR", "1990")),
            default_end_year=int(os.getenv("DEFAULT_END_YEAR", "2020")),
            model_dir=Path(os.getenv("MODEL_DIR", "data/models")),
            model_filename=os.getenv("MODEL_FILENAME", "climate_full.bin"),
            sample_model_filename=os.getenv("SAMPLE_MODEL_FILENAME", "climate_sample.bin"),
            use_sample_model=os.getenv("USE_SAMPLE_MODEL", "false").lower() == "true",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
