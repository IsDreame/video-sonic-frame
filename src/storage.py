import json
import os
import uuid

from src.config import settings


def generate_video_id() -> str:
    return uuid.uuid4().hex[:12]


def save_metadata(video_id: str, metadata: dict) -> None:
    filepath = os.path.join(settings.DATA_DIR, f"{video_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def load_metadata(video_id: str) -> dict | None:
    filepath = os.path.join(settings.DATA_DIR, f"{video_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
