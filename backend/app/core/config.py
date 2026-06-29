from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://sainext:sainext@db:5432/sainext"
    JWT_SECRET: str = "dev-secret-change-me-in-production-please-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30          # short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7             # long-lived refresh token
    REDIS_URL: str = "redis://redis:6379/0"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173"
    SEED_ON_STARTUP: bool = True

    # Security / ops
    ENV: str = "development"                        # development | production | test
    RATE_LIMIT_DEFAULT: str = "240/minute"         # per-IP global default
    RATE_LIMIT_LOGIN: str = "10/minute"            # per-IP login throttle
    ENABLE_RATE_LIMIT: bool = True
    ENABLE_HSTS: bool = False                       # set true behind HTTPS in prod

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_test(self) -> bool:
        return self.ENV == "test"


settings = Settings()
