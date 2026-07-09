import os

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models import (
    FrameResult,
    SearchRequest,
    SearchResponse,
    UploadResponse,
    VideoMetadata,
)
from app.services.search_service import search_segments
from app.services.transcription_service import transcribe
from app.services.video_service import extract_audio, extract_frame, frame_to_base64, get_video_duration
from app.storage import generate_video_id, load_metadata, save_metadata

router = APIRouter(tags=["videos"])

VIDEO_MIME_TYPES = {
    "video/mp4", "video/x-msvideo", "video/quicktime",
    "video/x-matroska", "video/webm", "video/x-flv",
    "video/x-ms-wmv", "video/mpeg",
}


@router.post("/videos/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    if not file.content_type or file.content_type not in VIDEO_MIME_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文件类型，请上传视频文件")

    video_id = generate_video_id()

    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    video_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
        f"{video_id}{ext}",
    )

    content = await file.read()
    with open(video_path, "wb") as f:
        f.write(content)

    duration = get_video_duration(video_path)

    audio_path = extract_audio(video_path)

    segments = transcribe(audio_path)

    transcript = " ".join(seg.text for seg in segments)

    metadata = VideoMetadata(
        video_id=video_id,
        filename=file.filename or "unknown",
        duration=duration,
        segments=segments,
    )
    save_metadata(video_id, metadata.model_dump())

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
    ext = os.path.splitext(metadata.filename)[1] or ".mp4"
    video_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
        f"{video_id}{ext}",
    )

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
    ext = os.path.splitext(metadata.filename)[1] or ".mp4"
    video_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
        f"{video_id}{ext}",
    )

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    frame_path = extract_frame(video_path, t)
    b64 = frame_to_base64(frame_path)

    return {"timestamp": t, "frame_base64": b64}
