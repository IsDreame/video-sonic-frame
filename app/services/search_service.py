from app.models import TranscriptionSegment


def search_segments(
    segments: list[TranscriptionSegment],
    query: str,
) -> list[dict]:
    """在转录片段中搜索关键词，返回匹配的片段信息。"""
    query_lower = query.lower()
    results = []

    for seg in segments:
        if query_lower in seg.text.lower():
            results.append({
                "text": seg.text,
                "start": seg.start,
                "end": seg.end,
            })

    return results
