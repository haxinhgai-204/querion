from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # -- Postgres --
    DATABASE_URL: str = (
        "postgresql+asyncpg://querion:querion_secret@localhost:5432/querion"
    )

    # -- Redis --
    REDIS_URL: str = "redis://localhost:6379/0"

    # -- MinIO --
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin_secret"
    MINIO_BUCKET: str = "querion-docs"
    MINIO_USE_SSL: bool = False

    # -- App --
    APP_NAME: str = "Querion API"
    DEBUG: bool = True

    # -- Auth / JWT --
    JWT_SECRET: str = "querion-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -- Super Admin Seed --
    SUPER_ADMIN_EMAIL: str = "admin@querion.io"
    SUPER_ADMIN_PASSWORD: str = "admin123"
    SUPER_ADMIN_NAME: str = "Super Admin"

    # -- Encryption --
    ENCRYPTION_KEY: str = ""

    model_config = {"env_file": [".env", "../../.env"], "extra": "ignore"}


settings = Settings()
