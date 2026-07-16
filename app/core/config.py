from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    sqlalchemy_database_url: str
    secret_key: SecretStr
    algorithm: str
    access_token_expire_minutes: int

    redis_url: str

    password_reset_token_expire_minutes: int = 30
    password_reset_token_length: int = 32
    
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool = True

    frontend_url: str


settings = Settings() # type: ignore