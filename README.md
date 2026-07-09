# Video Sonic Frame

视频转文字 + 文字定位帧服务。上传视频后自动使用 Whisper 进行语音转录（带时间戳），支持通过关键词搜索定位到对应的视频帧。

## 环境要求

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html)（必须安装并加入系统 PATH）

## 安装

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

通过环境变量或项目根目录下的 `.env` 文件进行配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WHISPER_MODEL` | `base` | Whisper 模型大小，可选 `tiny`/`base`/`small`/`medium`/`large` |
| `UPLOAD_DIR` | `./uploads` | 上传视频存储目录 |
| `FRAMES_DIR` | `./frames` | 提取的帧图片存储目录 |
| `DATA_DIR` | `./data` | 转录元数据 JSON 存储目录 |

示例 `.env` 文件：

```env
WHISPER_MODEL=base
```

> `base` 模型约 142MB，兼顾速度与准确率。如需更高准确率可设为 `small`（约 466MB）或 `large`（约 2.9GB）。

## 启动服务

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

启动后访问：
- API 文档（Swagger）：http://127.0.0.1:8000/docs
- API 服务：http://127.0.0.1:8000/api/v1

## API 使用

### 1. 上传视频并转文字

上传视频文件，自动提取音频并使用 Whisper 转录。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/videos/upload \
  -F "file=@your_video.mp4"
```

响应示例：

```json
{
  "video_id": "a1b2c3d4e5f6",
  "transcript": "大家好 欢迎收看今天的视频...",
  "segments": [
    { "text": "大家好", "start": 0.0, "end": 1.5 },
    { "text": "欢迎收看今天的视频", "start": 1.5, "end": 3.8 }
  ]
}
```

### 2. 获取视频转录结果

```bash
curl http://127.0.0.1:8000/api/v1/videos/a1b2c3d4e5f6
```

### 3. 按文字搜索定位帧

通过关键词搜索转录内容，返回匹配位置对应的视频帧图片（Base64 编码）。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/videos/a1b2c3d4e5f6/search \
  -H "Content-Type: application/json" \
  -d '{"query": "欢迎"}'
```

响应示例：

```json
{
  "matches": [
    {
      "timestamp": 0.0,
      "text": "大家好",
      "frame_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD..."
    }
  ],
  "total": 1
}
```

### 4. 按时间戳获取单帧

直接指定时间戳获取视频帧。

```bash
curl "http://127.0.0.1:8000/api/v1/videos/a1b2c3d4e5f6/frames?t=10.5"
```

响应示例：

```json
{
  "timestamp": 10.5,
  "frame_base64": "/9j/4AAQSkZJRg..."
}
```

## 工作流程

```
上传视频 → ffmpeg 提取音频(16kHz WAV) → Whisper 转录(带词级时间戳)
                                                    ↓
用户输入关键词 → 匹配转录片段 → 定位时间戳 → OpenCV 提取帧 → 返回 Base64 图片
```

## 目录结构

```
video-sonic-frame/
├── main.py              # 入口
├── app/
│   ├── __init__.py      # FastAPI 工厂
│   ├── config.py        # 配置
│   ├── models/          # Pydantic 数据模型
│   ├── services/        # 核心服务
│   │   ├── video_service.py           # 音频提取 + 帧提取
│   │   ├── transcription_service.py   # Whisper 转录
│   │   └── search_service.py          # 文字搜索
│   ├── routers/         # API 路由
│   └── storage.py       # 本地 JSON 存储
├── uploads/             # 上传视频（自动创建）
├── frames/              # 提取的帧图片（自动创建）
└── data/                # 转录元数据（自动创建）
```
