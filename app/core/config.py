from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    api_football_key: str = ""
    api_football_host: str = "api-football-v1.p.rapidapi.com"
    redis_url: str = "redis://localhost:6379"
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    live_score_ttl: int = 30
    fixtures_ttl: int = 300
    news_ttl: int = 600
    standings_ttl: int = 3600

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
