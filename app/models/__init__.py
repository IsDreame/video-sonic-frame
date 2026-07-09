from typing import Optional

from pydantic import BaseModel, Field


class TranscriptionSegment(BaseModel):
    text: str = Field(..., description="转录文本片段")
    start: float = Field(..., description="片段开始时间（秒）")
    end: float = Field(..., description="片段结束时间（秒）")


class VideoMetadata(BaseModel):
    video_id: str = Field(..., description="视频唯一ID")
    filename: str = Field(..., description="原始文件名")
    duration: Optional[float] = Field(None, description="视频时长（秒）")
    segments: list[TranscriptionSegment] = Field(default_factory=list, description="转录片段列表")


class UploadResponse(BaseModel):
    video_id: str = Field(..., description="视频唯一ID")
    transcript: str = Field(..., description="完整转录文本")
    segments: list[TranscriptionSegment] = Field(..., description="转录片段列表")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="搜索关键词或短语")


class FrameResult(BaseModel):
    timestamp: float = Field(..., description="帧所在时间戳（秒）")
    text: str = Field(..., description="匹配的转录文本")
    frame_base64: str = Field(..., description="帧图片的Base64编码")


class SearchResponse(BaseModel):
    matches: list[FrameResult] = Field(..., description="匹配的帧结果列表")
    total: int = Field(..., description="匹配总数")


class FrameQuery(BaseModel):
    t: float = Field(..., description="时间戳（秒）")
