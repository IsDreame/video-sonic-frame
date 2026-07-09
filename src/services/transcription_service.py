import logging
import os
import time
import warnings
from typing import Optional

import torch
import whisper

# Triton 内核非必需，缺少 CUDA Toolkit 时会回退，不影响 GPU 推理
warnings.filterwarnings("ignore", message="Failed to launch Triton kernels")

from src.config import settings
from src.models import TranscriptionSegment

logger = logging.getLogger(__name__)
_model: Optional[whisper.Whisper] = None
_converter: Optional[object] = None


def _get_converter():
    """延迟加载繁简转换器。"""
    global _converter
    if _converter is None:
        from opencc import OpenCC
        _converter = OpenCC("t2s")
    return _converter


def _resolve_device(config_value: str) -> str:
    """根据配置值解析计算设备。

    Args:
        config_value: 'auto' | 'cuda' | 'cpu'

    Returns:
        'cuda' 或 'cpu'
    """
    if config_value == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError(
                "配置要求使用 CUDA 设备，但 torch.cuda.is_available() 返回 False。"
                "请检查 CUDA 驱动和 PyTorch 安装。"
            )
        return "cuda"
    elif config_value == "cpu":
        return "cpu"
    elif config_value == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    else:
        raise ValueError(
            f"无效的 whisper.device 配置值: {config_value!r}，"
            f"应为 'auto'、'cuda' 或 'cpu'"
        )


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        device = _resolve_device(settings.WHISPER_DEVICE)
        logger.info("加载 Whisper 模型: model=%s, device=%s ...", settings.WHISPER_MODEL, device)
        t0 = time.perf_counter()
        _model = whisper.load_model(settings.WHISPER_MODEL, device=device)
        logger.info("Whisper 模型加载完成 (耗时 %.1fs)", time.perf_counter() - t0)
    return _model


def transcribe(audio_path: str) -> list[TranscriptionSegment]:
    """使用 Whisper 转录音频，返回带时间戳的片段列表。"""
    model = _get_model()
    device = _resolve_device(settings.WHISPER_DEVICE)

    transcribe_opts = {"word_timestamps": settings.WHISPER_WORD_TIMESTAMPS}
    if settings.WHISPER_LANGUAGE:
        transcribe_opts["language"] = settings.WHISPER_LANGUAGE
    if device == "cuda":
        transcribe_opts["fp16"] = True
    else:
        transcribe_opts["fp16"] = False

    logger.info("开始转录: %s (device=%s, language=%s, fp16=%s, word_timestamps=%s)",
                os.path.basename(audio_path),
                device, settings.WHISPER_LANGUAGE or "auto",
                transcribe_opts["fp16"], transcribe_opts["word_timestamps"])
    t0 = time.perf_counter()
    result = model.transcribe(audio_path, **transcribe_opts)
    elapsed = time.perf_counter() - t0

    segments = []
    convert = settings.WHISPER_CONVERT_TO_SIMPLIFIED
    cc = _get_converter() if convert else None
    for seg in result.get("segments", []):
        text = seg["text"].strip()
        if convert and cc:
            text = cc.convert(text)
        segments.append(TranscriptionSegment(
            text=text,
            start=round(seg["start"], 2),
            end=round(seg["end"], 2),
        ))

    logger.info("转录完成: %d 个片段, 音频时长约 %.0fs, 耗时 %.1fs, 速度 %.1fx%s",
                len(segments), segments[-1].end if segments else 0,
                elapsed, segments[-1].end / elapsed if segments and elapsed > 0 else 0,
                " (已转简体)" if convert else "")
    return segments
