# 视频转文字 + 文字定位帧 实现方案

## 一、需求摘要

实现一个 FastAPI 服务，支持：
1. **视频转文字**：上传视频文件，提取音频并使用 Whisper 进行语音转文字（带时间戳）
2. **文字定位帧**：通过文字关键词/短语搜索转录结果，定位到对应的视频帧，并返回帧图片

## 二、当前状态分析

| 项目 | 状态 |
|------|------|
| `main.py` | 已有入口，引用 `from app import create_app` |
| `app/` 模块 | 不存在，需新建 |
| `requirements.txt` | 已有 `fastapi`, `uvicorn`, `openai-whisper`, `opencv-python`, `numpy`, `pydantic` 等 |
| 外部依赖 | `ffmpeg` 需系统安装（Whisper 依赖它从视频提取音频） |

## 三、整体架构

```
video-sonic-frame/
├── main.py                    # 已有，无需修改
├── requirements.txt           # 已有，无需修改
├── app/
│   ├── __init__.py            # 新增：create_app() 工厂函数
│   ├── config.py              # 新增：Settings 配置类
│   ├── models/
│   │   └── __init__.py        # 新增：Pydantic 请求/响应模型
│   ├── services/
│   │   ├── __init__.py        # 新增：空文件
│   │   ├── video_service.py   # 新增：音频提取 + 帧提取（OpenCV）
│   │   ├── transcription_service.py  # 新增：Whisper 转录服务
│   │   └── search_service.py  # 新增：文字搜索 + 帧定位
│   ├── routers/
│   │   └── __init__.py        # 新增：空文件
│   │   └── video_router.py    # 新增：API 路由
│   └── storage.py             # 新增：JSON 本地存储（视频元数据 + 转录结果）
├── uploads/                   # 运行后自动创建，存储上传视频
├── frames/                    # 运行后自动创建，存储提取的帧图片
└── data/                      # 运行后自动创建，存储 metadata JSON
```

## 四、核心流程

### 流程 1：视频上传 → 转文字

```
用户上传视频 → 保存视频文件 → ffmpeg 提取音频 → Whisper 转录(带时间戳)
→ 存储转录结果 + 元数据 → 返回 video_id + 转录文本
```

### 流程 2：文字搜索 → 定位帧

```
用户输入关键词 → 在转录结果中匹配 → 获取匹配片段的时间戳
→ OpenCV 在对应时间戳提取帧 → 保存并返回帧图片(或Base64)
```

## 五、详细实现

### 5.1 `app/__init__.py` - 应用工厂

```python
from fastapi import FastAPI
from app.routers.video_router import router as video_router

def create_app() -> FastAPI:
    app = FastAPI(title="Video Sonic Frame")
    app.include_router(video_router, prefix="/api/v1")
    return app
```

### 5.2 `app/config.py` - 配置

使用 `pydantic-settings`，从环境变量读取配置：

- `UPLOAD_DIR`: 上传视频目录，默认 `./uploads`
- `FRAMES_DIR`: 帧图片目录，默认 `./frames`  
- `DATA_DIR`: 元数据目录，默认 `./data`
- `WHISPER_MODEL`: Whisper 模型大小，默认 `base`
- `FFMPEG_PATH`: ffmpeg 路径，默认 `ffmpeg`（从 PATH 查找）

### 5.3 `app/models/__init__.py` - 数据模型

| 模型 | 用途 |
|------|------|
| `TranscriptionSegment` | 单个转录片段：text, start(秒), end(秒) |
| `VideoMetadata` | 视频元数据：video_id, filename, duration, segments[] |
| `UploadResponse` | 上传响应：video_id, transcript, segments |
| `SearchRequest` | 搜索请求：keyword/query |
| `FrameResult` | 帧结果：timestamp, text, frame_base64 |
| `SearchResponse` | 搜索响应：matches[] (FrameResult), total |

### 5.4 `app/services/video_service.py` - 视频处理

**音频提取** `extract_audio(video_path) -> audio_path`:
- 使用 `subprocess` 调用 ffmpeg：`ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav`
- 输出 16kHz 单声道 WAV（Whisper 最佳输入格式）

**帧提取** `extract_frame(video_path, timestamp_seconds) -> frame_path`:
- 使用 OpenCV `cv2.VideoCapture` 定位到指定时间戳
- 读取帧并保存为 JPEG
- 返回帧图片路径

**帧转 Base64** `frame_to_base64(frame_path) -> str`:
- 读取帧图片，转 Base64 字符串返回

### 5.5 `app/services/transcription_service.py` - 转录服务

**转录** `transcribe(audio_path) -> list[TranscriptionSegment]`:
- 加载 Whisper 模型（单例，避免重复加载）
- 调用 `model.transcribe(audio_path, word_timestamps=True)` 
- 提取 segments，转换为 `TranscriptionSegment` 列表
- 使用 `word_timestamps=True` 获得细粒度时间戳

### 5.6 `app/services/search_service.py` - 搜索服务

**搜索** `search(segments, query) -> list[dict]`:
- 遍历所有 segments，对每个 segment 的 text 做子串匹配（大小写不敏感）
- 返回匹配的 segment 及其时间戳

### 5.7 `app/routers/video_router.py` - API 路由

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/videos/upload` | 上传视频，触发转录，返回 video_id + transcript |
| GET | `/api/v1/videos/{video_id}` | 获取视频元数据和完整转录 |
| POST | `/api/v1/videos/{video_id}/search` | 按文字搜索，返回匹配的帧（Base64） |
| GET | `/api/v1/videos/{video_id}/frames?t={timestamp}` | 获取指定时间戳的单帧图片 |

### 5.8 `app/storage.py` - 存储层

基于 JSON 文件的简单存储：
- `save_metadata(video_id, metadata)` → 写入 `data/{video_id}.json`
- `load_metadata(video_id)` → 读取 `data/{video_id}.json`
- `generate_video_id()` → 生成唯一 ID（UUID）

## 六、依赖与前提

| 依赖 | 说明 |
|------|------|
| ffmpeg | **必须系统安装**，用于音频提取。Whisper 内部也依赖它。 |
| openai-whisper | 已在 `requirements.txt` 中 |
| opencv-python | 已在 `requirements.txt` 中 |

## 七、验证步骤

1. 启动服务：`uvicorn main:app --reload`
2. 上传视频：`POST /api/v1/videos/upload`（multipart/form-data，字段名 `file`）
3. 验证转录：检查返回的 transcript 和 segments 时间戳
4. 搜索帧：`POST /api/v1/videos/{video_id}/search`，body `{"query": "关键词"}`
5. 检查返回的帧图片（Base64）是否正确
