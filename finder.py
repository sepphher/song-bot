"""Collects song candidates from several sources into one ordered pool."""
import asyncio
import hashlib
import aiohttp
from shazamio import Shazam
from config import AUDD_TOKEN


def make_id(title, artist):
    return hashlib.sha1(f"{title}|{artist}".lower().encode()).hexdigest()[:10]


def cand(title, artist, url=""):
    return {"id": make_id(title, artist), "title": title, "artist": artist, "url": url}


async def from_shazam(path):
    r = await Shazam().recognize(path)
    t = r.get("track")
    return [cand(t["title"], t["subtitle"], t.get("url", ""))] if t else []


async def from_audd(path):
    if not AUDD_TOKEN:
        return []
    with open(path, "rb") as f:
        form = aiohttp.FormData()
        form.add_field("api_token", AUDD_TOKEN)
        form.add_field("file", f.read(), filename="a.mp3")
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.audd.io/", data=form) as r:
            j = await r.json(content_type=None)
    res = j.get("result")
    return [cand(res["title"], res["artist"], res.get("song_link", ""))] if res else []


async def from_itunes(term, limit=5):
    if not term or not term.strip():
        return []
    async with aiohttp.ClientSession() as s:
        async with s.get("https://itunes.apple.com/search",
                         params={"term": term, "media": "music", "limit": limit}) as r:
            j = await r.json(content_type=None)
    return [cand(x["trackName"], x["artistName"], x.get("trackViewUrl", ""))
            for x in j.get("results", []) if "trackName" in x]


async def build_pool(audio, meta, max_items=8):
    found = []
    if audio:
        results = await asyncio.gather(from_shazam(audio), from_audd(audio),
                                       return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                found += r
    if meta.get("track"):
        found.append(cand(meta["track"], meta.get("artist", "")))
    # "similar" songs: same artist as best match, or caption text as fallback
    seed = found[0]["artist"] if found else meta.get("caption", "")
    try:
        found += await from_itunes(seed)
    except Exception:
        pass
    seen, out = set(), []
    for c in found:
        if c["id"] not in seen:
            seen.add(c["id"])
            out.append(c)
    return out[:max_items]
