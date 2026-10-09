import os
import subprocess
import tempfile
import yt_dlp
from cryptography.fernet import Fernet
from config import COOKIES_ENC, COOKIES_KEY


def _cookie_file():
    """Decrypt the encrypted Instagram cookies into a temp file (or None)."""
    if COOKIES_KEY and os.path.exists(COOKIES_ENC):
        with open(COOKIES_ENC, "rb") as f:
            data = Fernet(COOKIES_KEY.encode()).decrypt(f.read())
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(data)
        tmp.close()
        return tmp.name
    return None


def download(url, workdir):
    """Blocking. Returns (video_path, meta). Run with asyncio.to_thread."""
    cookie = _cookie_file()
    opts = {"outtmpl": f"{workdir}/media.%(ext)s", "format": "mp4/best",
            "quiet": True, "noplaylist": True}
    if cookie:
        opts["cookiefile"] = cookie
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
            path = y.prepare_filename(info)
    finally:
        if cookie:
            os.remove(cookie)
    meta = {
        "id": str(info.get("id") or url),
        "track": info.get("track"),
        "artist": info.get("artist") or info.get("uploader") or "",
        "caption": (info.get("description") or info.get("title") or "")[:80],
    }
    return path, meta


def extract_audio(video, audio, seconds=15):
    subprocess.run(["ffmpeg", "-y", "-i", video, "-t", str(seconds),
                    "-vn", "-ac", "1", audio],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
