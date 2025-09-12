from functools import lru_cache
from pathlib import Path
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    app_name: str = "Climate API"
    api_v1_prefix: str = "/api/v1"
    default_start_year: int = 1990
    default_end_year: int = 2020
    model_dir: Path = Field(default_factory=lambda: Path("data/models"))
    model_filename: str = "climate_full.bin"  # full size (~400MB) expected
    sample_model_filename: str = "climate_sample.bin"  # tiny test model (~1MB)
    use_sample_model: bool = False  # toggle for tests/dev

    @property
    def active_model_path(self) -> Path:
        name = self.sample_model_filename if self.use_sample_model else self.model_filename
        return self.model_dir / name

    @validator("model_dir", pre=True)
    def _expand_dir(cls, v):  # noqa: D401
        return Path(v)

    class Config:
        env_file = ".env"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
