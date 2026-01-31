from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    GROK_API_KEY: str
    AT_USERNAME: str
    AT_API_KEY: str
    DATABASE_URL: str
    APP_SECRET: str
    DEFAULT_LANGUAGE: str = "en"
    SMS_DISCLAIMER: str
    CHW_PHONE: str
    TEA_CHW_PHONE: str = ""
    FARM_CLINIC_NUMBER: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True
    )


settings = Settings()
