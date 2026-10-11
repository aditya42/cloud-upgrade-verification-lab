from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/upgrade_lab"
    )
    app_version: str = os.getenv("APP_VERSION", "v2.0")


settings = Settings()
