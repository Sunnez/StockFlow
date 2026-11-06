from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    db_echo: bool = False
    test_database_url: str | None = None

    auth_allowed_origins: list[str]
    csrf_secret_key: SecretStr

    jwt_secret_key: SecretStr
    jwt_access_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
    )
    auth_cookie_secure: bool = True

    auth_session_expire_days: int = Field(
        default=30,
        ge=1,
        le=90,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
