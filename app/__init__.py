from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.video_router import router as video_router


def create_app() -> FastAPI:
    app = FastAPI(title="Video Sonic Frame")
    app.include_router(video_router, prefix="/api/v1")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
    return app
