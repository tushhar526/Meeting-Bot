from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
from datetime import timedelta
from functools import cached_property


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    SECRET_KEY: str
    ALGORITHM: str

    REDIS_URL: str
    REDIS_DATA_EXPIRE: int

    COOKIE_SECURE: bool
    COOKIE_HTTPONLY: bool
    COOKIE_SAMESITE: str

    ACCESS_TOKEN_EXPIRE: int
    REFRESH_TOKEN_EXPIRE: int
    VERIFICATION_TOKEN_EXPIRE: int

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str

    @property
    def DATABASE_URL(self):
        password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg2://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @cached_property
    def TOKEN_CONFIG(self):
        return {
            "access": {
                "cookie_name": "access_token",
                "expiry": timedelta(minutes=self.ACCESS_TOKEN_EXPIRE).total_seconds(),
            },
            "refresh": {
                "cookie_name": "refresh_token",
                "expiry": timedelta(days=self.REFRESH_TOKEN_EXPIRE).total_seconds(),
            },
            "verification": {
                "cookie_name": "verification_token",
                "expiry": timedelta(
                    minutes=self.VERIFICATION_TOKEN_EXPIRE
                ).total_seconds(),
            },
        }

    class Config:
        env_file = ".env"


setting = Settings()
