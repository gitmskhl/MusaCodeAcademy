from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from dotenv import dotenv_values
import os
import re

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

    sqlalchemy_database_url: str
    secret_key: SecretStr
    algorithm: str
    access_token_expire_minutes: int

    redis_url: str

    ai_model: str = ""
    ai_models: list[str] = Field(default_factory=list)
    ai_api_key: SecretStr = SecretStr("")

    password_reset_token_expire_minutes: int = 30
    password_reset_token_length: int = 32
    
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool = True

    frontend_url: str

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        def numbered_models():
            files = dotenv_settings.env_file
            if isinstance(files, (str, os.PathLike)):
                files = [files]
            values = {}
            for path in files or []:
                values.update({key.upper(): value for key, value in dotenv_values(
                    path, encoding=dotenv_settings.env_file_encoding or "utf-8"
                ).items()})
            values.update({key.upper(): value for key, value in os.environ.items()})
            numbered = sorted(
                ((int(key.removeprefix("AI_MODEL_")), key, value.strip())
                 for key, value in values.items()
                 if re.fullmatch(r"AI_MODEL_[0-9]+", key) and value and value.strip()),
            )
            return {"ai_models": list(dict.fromkeys(value for _, _, value in numbered))}

        return init_settings, env_settings, dotenv_settings, file_secret_settings, numbered_models

    def available_ai_models(self) -> list[str]:
        models = self.ai_models or [self.ai_model]
        return list(dict.fromkeys(model.strip() for model in models if model.strip()))


settings = Settings() # type: ignore
