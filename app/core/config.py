from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE: int
    REFRESH_TOKEN_EXPIRE: int

    @property
    def DATABASE_URL(self):
        password = quote_plus(self.DB_PASSWORD)
        return f"postgresql+psycopg2://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


setting = Settings()