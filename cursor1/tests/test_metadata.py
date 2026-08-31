"""Tests for video metadata extraction."""

from app.downloader.metadata import VideoMetadata


def test_video_metadata_from_ytdlp_info() -> None:
    info = {
        "title": "Video by chef",
        "uploader": "Chef Name",
        "channel": "chef_handle",
        "uploader_id": "12345",
        "description": "1 cup rice\n2 tbsp soy sauce",
        "upload_date": "20260101",
        "like_count": 100,
        "comment_count": 2,
        "comments": [
            {"author": "user1", "text": "Full recipe in comments!", "timestamp": 1700000000},
            {"author": "user2", "text": "  ", "timestamp": 1700000001},
        ],
    }
    meta = VideoMetadata.from_ytdlp_info(
        info,
        source_url="https://www.instagram.com/reel/ABC123/",
        reel_id="ABC123",
    )
    assert meta.title == "Video by chef"
    assert meta.author == "Chef Name"
    assert meta.author_username == "chef_handle"
    assert meta.caption == "1 cup rice\n2 tbsp soy sauce"
    assert meta.comment_count == 2
    assert len(meta.comments) == 1
    assert meta.comments[0].text == "Full recipe in comments!"
