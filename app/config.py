import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    FRAMES_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frames")
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    WHISPER_MODEL: str = "base"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FRAMES_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
