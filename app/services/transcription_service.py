from typing import Optional

import whisper

from app.config import settings
from app.models import TranscriptionSegment

_model: Optional[whisper.Whisper] = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        _model = whisper.load_model(settings.WHISPER_MODEL)
    return _model


def transcribe(audio_path: str) -> list[TranscriptionSegment]:
    """使用 Whisper 转录音频，返回带时间戳的片段列表。"""
    model = _get_model()
    result = model.transcribe(audio_path, word_timestamps=True)

    segments = []
    for seg in result.get("segments", []):
        segments.append(TranscriptionSegment(
            text=seg["text"].strip(),
            start=round(seg["start"], 2),
            end=round(seg["end"], 2),
        ))
    return segments
