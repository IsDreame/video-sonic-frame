import base64
import os
import subprocess

import cv2

from app.config import settings


def extract_audio(video_path: str) -> str:
    """从视频文件中提取音频，返回音频文件路径。"""
    audio_dir = os.path.join(settings.UPLOAD_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(audio_dir, f"{video_basename}.wav")

    if os.path.exists(audio_path):
        return audio_path

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）。"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if fps > 0:
        return round(frame_count / fps, 2)
    return 0.0


def extract_frame(video_path: str, timestamp_seconds: float) -> str:
    """从视频中提取指定时间戳的帧，保存为 JPEG，返回图片路径。"""
    frames_dir = settings.FRAMES_DIR
    os.makedirs(frames_dir, exist_ok=True)

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    ts_str = f"{timestamp_seconds:.2f}".replace(".", "_")
    frame_path = os.path.join(frames_dir, f"{video_basename}_{ts_str}.jpg")

    if os.path.exists(frame_path):
        return frame_path

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    target_frame = int(timestamp_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise ValueError(f"无法在时间戳 {timestamp_seconds}s 处提取帧")

    cv2.imwrite(frame_path, frame)
    return frame_path


def frame_to_base64(frame_path: str) -> str:
    """读取帧图片并转为 Base64 字符串。"""
    with open(frame_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
