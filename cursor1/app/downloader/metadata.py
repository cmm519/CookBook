"""Instagram video metadata extracted from yt-dlp."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class CommentEntry(BaseModel):
    author: str
    author_id: str | None = None
    text: str
    timestamp: int | None = None
    like_count: int | None = None


class VideoMetadata(BaseModel):
    reel_id: str
    source_url: str
    title: str | None = None
    author: str | None = None
    author_username: str | None = None
    author_id: str | None = None
    caption: str | None = None
    upload_date: str | None = None
    like_count: int | None = None
    comment_count: int | None = None
    comments: list[CommentEntry] = Field(default_factory=list)
    extracted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def from_ytdlp_info(cls, info: dict[str, Any], *, source_url: str, reel_id: str) -> VideoMetadata:
        comments_raw = info.get("comments")
        comments: list[CommentEntry] = []
        if isinstance(comments_raw, list):
            for item in comments_raw:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                comments.append(
                    CommentEntry(
                        author=str(item.get("author") or "unknown"),
                        author_id=str(item["author_id"]) if item.get("author_id") is not None else None,
                        text=text.strip(),
                        timestamp=item.get("timestamp") if isinstance(item.get("timestamp"), int) else None,
                        like_count=item.get("like_count") if isinstance(item.get("like_count"), int) else None,
                    )
                )

        upload_date = info.get("upload_date")
        return cls(
            reel_id=reel_id,
            source_url=source_url,
            title=info.get("title") if isinstance(info.get("title"), str) else None,
            author=info.get("uploader") if isinstance(info.get("uploader"), str) else None,
            author_username=info.get("channel") if isinstance(info.get("channel"), str) else None,
            author_id=str(info["uploader_id"]) if info.get("uploader_id") is not None else None,
            caption=info.get("description") if isinstance(info.get("description"), str) else None,
            upload_date=str(upload_date) if upload_date is not None else None,
            like_count=info.get("like_count") if isinstance(info.get("like_count"), int) else None,
            comment_count=info.get("comment_count") if isinstance(info.get("comment_count"), int) else None,
            comments=comments,
        )
