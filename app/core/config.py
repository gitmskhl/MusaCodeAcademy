from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    secret_key: SecretStr