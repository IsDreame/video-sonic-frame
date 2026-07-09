import base64
import logging
import os
import subprocess
import time

import cv2

from src.config import settings

logger = logging.getLogger(__name__)


def extract_audio(video_path: str) -> str:
    """从视频文件中提取音频，返回音频文件路径。"""
    audio_dir = os.path.join(settings.UPLOAD_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(audio_dir, f"{video_basename}.wav")

    if os.path.exists(audio_path):
        logger.debug("音频缓存命中: %s", audio_path)
        return audio_path

    cmd = [
        settings.FFMPEG_PATH, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", settings.AUDIO_CODEC,
        "-ar", settings.AUDIO_SAMPLE_RATE,
        "-ac", settings.AUDIO_CHANNELS,
        audio_path,
    ]
    logger.debug("执行 ffmpeg: %s", " ".join(cmd))
    t0 = time.perf_counter()
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else "(无输出)"
        logger.error("ffmpeg 执行失败 (返回码 %d): %s", e.returncode, stderr_msg)
        raise RuntimeError(
            f"ffmpeg 音频提取失败 (返回码 {e.returncode}): {stderr_msg}"
        ) from e
    elapsed = time.perf_counter() - t0
    audio_size_kb = os.path.getsize(audio_path) / 1024
    logger.debug("音频提取耗时 %.1fs, 输出大小 %.1fKB: %s", elapsed, audio_size_kb, audio_path)
    return audio_path


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）。"""
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps > 0:
            return round(frame_count / fps, 2)
        return 0.0
    finally:
        cap.release()


def extract_frame(video_path: str, timestamp_seconds: float) -> str:
    """从视频中提取指定时间戳的帧，保存为 JPEG，返回图片路径。"""
    frames_dir = settings.FRAMES_DIR
    os.makedirs(frames_dir, exist_ok=True)

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    ts_str = f"{timestamp_seconds:.2f}".replace(".", "_")
    frame_path = os.path.join(frames_dir, f"{video_basename}_{ts_str}.jpg")

    if os.path.exists(frame_path):
        logger.debug("帧缓存命中: timestamp=%.2fs, path=%s", timestamp_seconds, frame_path)
        return frame_path

    logger.debug("提取帧: video=%s, timestamp=%.2fs", video_basename, timestamp_seconds)
    cap = cv2.VideoCapture(video_path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = settings.DEFAULT_FPS
            logger.debug("无法获取原始帧率，使用默认值: %.1f", fps)

        target_frame = int(timestamp_seconds * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()

        if not ret or frame is None:
            logger.error("帧提取失败: timestamp=%.2fs, target_frame=%d, fps=%.1f", timestamp_seconds, target_frame, fps)
            raise ValueError(f"无法在时间戳 {timestamp_seconds}s 处提取帧")

        cv2.imwrite(frame_path, frame)
        logger.debug("帧已保存: %s", frame_path)
        return frame_path
    finally:
        cap.release()


def frame_to_base64(frame_path: str) -> str:
    """读取帧图片并转为 Base64 字符串。"""
    with open(frame_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
