from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Lavrari"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "prod"

    MONGODB_CONNECTION_STRING: str = ""
    MONGODB_DATABASE_NAME: str = "lavrari"

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # IBM Cloud Object Storage (HMAC credentials)
    IBM_COS_ENDPOINT: str = ""        # ex: https://s3.br-sao.cloud-object-storage.appdomain.cloud
    IBM_COS_ACCESS_KEY: str = ""      # cos_hmac_keys.access_key_id
    IBM_COS_SECRET_KEY: str = ""      # cos_hmac_keys.secret_access_key
    IBM_COS_BUCKET_NAME: str = "lavrari"
    IBM_COS_INSTANCE_CRN: str = ""    # resource_instance_id do JSON
    GROQ_API_KEY: str = ""

    WEATHER_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
