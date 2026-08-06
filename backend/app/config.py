from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secure_password"
    POSTGRES_DB: str = "discord_analytics"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    POSTGRES_READONLY_USER: str = "discord_readonly"
    POSTGRES_READONLY_PASSWORD: str = "readonly_secure_password"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ARTIFACTS_DIR: str = "./artifacts"
    MAX_SQL_ROW_LIMIT: int = 1000
    SQL_TIMEOUT_SECONDS: float = 5.0

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def database_url_write(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def database_url_readonly(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_READONLY_USER}:{self.POSTGRES_READONLY_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
