import pytest

from app.downloader import UnsupportedURLError, is_supported_url
from app.downloader.base import Downloader


def test_supported_urls():
    assert is_supported_url("https://www.instagram.com/reel/ABC123/")
    assert is_supported_url("https://youtu.be/xyz")
    assert is_supported_url("https://www.tiktok.com/@user/video/1")


def test_unsupported_urls():
    assert not is_supported_url("ftp://instagram.com/reel/ABC123/")
    assert not is_supported_url("https://example.com/video")
    assert not is_supported_url("not a url")


def test_validate_raises_on_unsupported():
    class _Dummy(Downloader):
        def download(self, url, dest_dir):  # pragma: no cover - not called
            raise NotImplementedError

    with pytest.raises(UnsupportedURLError):
        _Dummy().validate("https://example.com/video")
