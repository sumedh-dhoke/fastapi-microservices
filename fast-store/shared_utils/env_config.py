import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Detect the current environment (defaults to 'development')
env_state = os.getenv("APP_ENV", "dev")

class Settings(BaseSettings):
    JWT_SECRET_KEY: str
    DEBUG_MODE: bool

    # 2. Dynamically load the correct .env file
    model_config = SettingsConfigDict(env_file=f".env.{env_state}")

settings = Settings()
