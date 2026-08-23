from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    NAME: str = "stackai-authz"
    ENV: str = "local"
    SUPABASE_URL: str | None = None
    DATABASE_URL: str | None = None
    JWT_AUDIENCE: str = "authenticated"
    DEBUG: bool = False


settings = Settings()
