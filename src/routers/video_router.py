import logging
import os
import time

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from src.config import settings
from src.models import (
    FrameResult,
    SearchRequest,
    SearchResponse,
    UploadResponse,
    VideoMetadata,
)
from src.services.search_service import search_segments
from src.services.transcription_service import transcribe
from src.services.video_service import extract_audio, extract_frame, frame_to_base64, get_video_duration
from src.storage import generate_video_id, load_metadata, save_metadata

logger = logging.getLogger(__name__)
router = APIRouter(tags=["videos"])


@router.post("/videos/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    t_start = time.perf_counter()
    logger.info("接收到上传请求: filename=%s, content_type=%s, size=%s",
                file.filename, file.content_type,
                f"{file.size / 1024 / 1024:.1f}MB" if file.size else "未知")

    if not file.content_type or file.content_type not in settings.ALLOWED_MIME_TYPES:
        logger.warning("不支持的文件类型被拒绝: %s", file.content_type)
        raise HTTPException(status_code=400, detail="不支持的文件类型，请上传视频文件")

    video_id = generate_video_id()
    logger.info("[%s] 生成视频ID", video_id)

    ext = os.path.splitext(file.filename or "video.mp4")[1] or settings.DEFAULT_VIDEO_EXTENSION
    video_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")

    content = await file.read()
    with open(video_path, "wb") as f:
        f.write(content)
    file_size_mb = len(content) / 1024 / 1024
    logger.info("[%s] 文件已保存: %s (%.1fMB), 耗时 %.1fs",
                video_id, video_path, file_size_mb, time.perf_counter() - t_start)

    t1 = time.perf_counter()
    duration = get_video_duration(video_path)
    logger.info("[%s] 视频时长: %.1fs (检测耗时 %.1fs)", video_id, duration, time.perf_counter() - t1)

    t2 = time.perf_counter()
    audio_path = extract_audio(video_path)
    logger.info("[%s] 音频提取完成: %s (耗时 %.1fs)", video_id, audio_path, time.perf_counter() - t2)

    t3 = time.perf_counter()
    segments = transcribe(audio_path)
    logger.info("[%s] 转录完成: %d 个片段 (耗时 %.1fs)", video_id, len(segments), time.perf_counter() - t3)

    transcript = " ".join(seg.text for seg in segments)

    metadata = VideoMetadata(
        video_id=video_id,
        filename=file.filename or "unknown",
        duration=duration,
        segments=segments,
    )
    save_metadata(video_id, metadata.model_dump())
    logger.info("[%s] 元数据已保存, 总耗时 %.1fs", video_id, time.perf_counter() - t_start)

    return UploadResponse(
        video_id=video_id,
        transcript=transcript,
        segments=segments,
    )


@router.get("/videos/{video_id}", response_model=VideoMetadata)
async def get_video(video_id: str):
    data = load_metadata(video_id)
    if data is None:
        raise HTTPException(status_code=404, detail="视频不存在")
    return VideoMetadata(**data)


@router.post("/videos/{video_id}/search", response_model=SearchResponse)
async def search_video(video_id: str, req: SearchRequest):
    data = load_metadata(video_id)
    if data is None:
        raise HTTPException(status_code=404, detail="视频不存在")

    metadata = VideoMetadata(**data)
    ext = os.path.splitext(metadata.filename)[1] or settings.DEFAULT_VIDEO_EXTENSION
    video_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    matched = search_segments(metadata.segments, req.query)

    results = []
    for m in matched:
        ts = m["start"]
        frame_path = extract_frame(video_path, ts)
        b64 = frame_to_base64(frame_path)
        results.append(FrameResult(
            timestamp=ts,
            text=m["text"],
            frame_base64=b64,
        ))

    return SearchResponse(matches=results, total=len(results))


@router.get("/videos/{video_id}/frames")
async def get_frame(video_id: str, t: float = Query(..., description="时间戳（秒）")):
    data = load_metadata(video_id)
    if data is None:
        raise HTTPException(status_code=404, detail="视频不存在")

    metadata = VideoMetadata(**data)
    ext = os.path.splitext(metadata.filename)[1] or settings.DEFAULT_VIDEO_EXTENSION
    video_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    frame_path = extract_frame(video_path, t)
    b64 = frame_to_base64(frame_path)

    return {"timestamp": t, "frame_base64": b64}


@router.get("/videos/{video_id}/file")
async def get_video_file(video_id: str):
    """返回视频文件，供前端播放器使用。"""
    data = load_metadata(video_id)
    if data is None:
        raise HTTPException(status_code=404, detail="视频不存在")

    metadata = VideoMetadata(**data)
    ext = os.path.splitext(metadata.filename)[1] or settings.DEFAULT_VIDEO_EXTENSION
    video_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}{ext}")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    return FileResponse(video_path, media_type=f"video/{ext.lstrip('.')}")
