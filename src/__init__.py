from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.routers.video_router import router as video_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_TITLE)
    app.include_router(video_router, prefix=settings.API_PREFIX)
    app.mount("/", StaticFiles(directory=settings.STATIC_DIR, html=True), name="static")
    return app
