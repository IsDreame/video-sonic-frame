import os

import yaml


_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config.yaml")


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Settings:
    def __init__(self) -> None:
        self._data = _load_config()

    @property
    def APP_TITLE(self) -> str:
        return self._data["app"]["title"]

    @property
    def APP_HOST(self) -> str:
        return self._data["app"]["host"]

    @property
    def APP_PORT(self) -> int:
        return self._data["app"]["port"]

    @property
    def API_PREFIX(self) -> str:
        return self._data["app"]["api_prefix"]

    @property
    def STATIC_DIR(self) -> str:
        return os.path.join(_PROJECT_ROOT, self._data["app"]["static_dir"])

    @property
    def UPLOAD_DIR(self) -> str:
        return os.path.join(_PROJECT_ROOT, self._data["paths"]["upload_dir"])

    @property
    def FRAMES_DIR(self) -> str:
        return os.path.join(_PROJECT_ROOT, self._data["paths"]["frames_dir"])

    @property
    def DATA_DIR(self) -> str:
        return os.path.join(_PROJECT_ROOT, self._data["paths"]["data_dir"])

    @property
    def WHISPER_MODEL(self) -> str:
        return self._data["whisper"]["model"]

    @property
    def WHISPER_WORD_TIMESTAMPS(self) -> bool:
        return self._data["whisper"]["word_timestamps"]

    @property
    def WHISPER_CONVERT_TO_SIMPLIFIED(self) -> bool:
        return self._data["whisper"].get("convert_to_simplified", False)

    @property
    def WHISPER_DEVICE(self) -> str:
        return self._data["whisper"].get("device", "auto")

    @property
    def WHISPER_LANGUAGE(self) -> str:
        return self._data["whisper"].get("language", "")

    @property
    def ALLOWED_MIME_TYPES(self) -> set[str]:
        return set(self._data["video"]["allowed_mime_types"])

    @property
    def DEFAULT_VIDEO_EXTENSION(self) -> str:
        return self._data["video"]["default_extension"]

    @property
    def DEFAULT_FPS(self) -> float:
        return self._data["video"]["default_fps"]

    @property
    def FFMPEG_PATH(self) -> str:
        return self._data["audio"]["ffmpeg_path"]

    @property
    def AUDIO_CODEC(self) -> str:
        return self._data["audio"]["codec"]

    @property
    def AUDIO_SAMPLE_RATE(self) -> str:
        return self._data["audio"]["sample_rate"]

    @property
    def AUDIO_CHANNELS(self) -> str:
        return self._data["audio"]["channels"]


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FRAMES_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
