from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Code Commanders Marketplace API"
    secret_key: str = "change-this-secret-in-production"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./marketplace.db"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
