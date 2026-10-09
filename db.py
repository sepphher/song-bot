"""SQLite storage shared by both bots. File lives on disk (WAL mode), so data
survives restarts/shutdowns. Everything is keyed by Telegram user_id."""
import os
import aiosqlite
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks(
    track_id TEXT PRIMARY KEY, title TEXT, artist TEXT, url TEXT);
CREATE TABLE IF NOT EXISTS pool(
    user_id INTEGER, src TEXT, track_id TEXT, pos INTEGER,
    PRIMARY KEY(user_id, src, track_id));
CREATE TABLE IF NOT EXISTS rejected(
    user_id INTEGER, src TEXT, track_id TEXT,
    PRIMARY KEY(user_id, src, track_id));
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY, lang TEXT);
CREATE TABLE IF NOT EXISTS playlist(
    user_id INTEGER, track_id TEXT, added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, track_id));
"""


def _conn():
    return aiosqlite.connect(DB_PATH, timeout=15)


async def init():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with _conn() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()


async def save_tracks(cands):
    async with _conn() as db:
        await db.executemany(
            "INSERT OR IGNORE INTO tracks VALUES(?,?,?,?)",
            [(c["id"], c["title"], c["artist"], c.get("url", "")) for c in cands])
        await db.commit()


async def set_pool(uid, src, cands):
    async with _conn() as db:
        await db.execute("DELETE FROM pool WHERE user_id=? AND src=?", (uid, src))
        await db.executemany(
            "INSERT OR IGNORE INTO pool VALUES(?,?,?,?)",
            [(uid, src, c["id"], i) for i, c in enumerate(cands)])
        await db.commit()


async def get_pool(uid, src):
    """Candidates for this post that the user has NOT rejected, best first."""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT t.track_id AS id, t.title, t.artist, t.url
               FROM pool p JOIN tracks t ON t.track_id = p.track_id
               WHERE p.user_id=? AND p.src=?
                 AND p.track_id NOT IN
                   (SELECT track_id FROM rejected WHERE user_id=? AND src=?)
               ORDER BY p.pos""", (uid, src, uid, src))
        return [dict(r) for r in await cur.fetchall()]


async def reject(uid, src, tid):
    async with _conn() as db:
        await db.execute("INSERT OR IGNORE INTO rejected VALUES(?,?,?)", (uid, src, tid))
        await db.commit()


async def get_track(tid):
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT track_id AS id, title, artist, url FROM tracks WHERE track_id=?", (tid,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def add_playlist(uid, tid):
    async with _conn() as db:
        await db.execute("INSERT OR IGNORE INTO playlist(user_id, track_id) VALUES(?,?)", (uid, tid))
        await db.commit()


async def get_playlist(uid):
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT t.track_id AS id, t.title, t.artist, t.url
               FROM playlist pl JOIN tracks t ON t.track_id = pl.track_id
               WHERE pl.user_id=? ORDER BY pl.added_at""", (uid,))
        return [dict(r) for r in await cur.fetchall()]


async def remove_playlist(uid, tid):
    async with _conn() as db:
        await db.execute("DELETE FROM playlist WHERE user_id=? AND track_id=?", (uid, tid))
        await db.commit()


async def clear_playlist(uid):
    async with _conn() as db:
        await db.execute("DELETE FROM playlist WHERE user_id=?", (uid,))
        await db.commit()


async def delete_user(uid):
    async with _conn() as db:
        for t in ("pool", "rejected", "playlist", "users"):
            await db.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
        await db.commit()


async def set_lang(uid, lang):
    async with _conn() as db:
        await db.execute(
            "INSERT INTO users(user_id, lang) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang", (uid, lang))
        await db.commit()


async def get_lang(uid):
    async with _conn() as db:
        cur = await db.execute("SELECT lang FROM users WHERE user_id=?", (uid,))
        r = await cur.fetchone()
        return r[0] if r and r[0] else "en"
