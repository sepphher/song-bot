"""Main bot. Pick language -> send a name / lyrics / voice / audio / video /
video note / link (Instagram, TikTok, YouTube...) -> get 2 song candidates."""
import asyncio
import hashlib
import logging
import os
import re
import tempfile

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart

import db
import finder
from config import BOT_TOKEN, PLAYLIST_BOT_TOKEN, PLAYLIST_BOT_USERNAME
from downloader import download, extract_audio
from i18n import LANGS, PICK, t

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Allow-list of sites (prevents users from making the server fetch arbitrary URLs).
# Host must END with one of these domains and be followed by "/".
URL_RE = re.compile(
    r"https?://(?:[\w-]+\.)*(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be|"
    r"soundcloud\.com|twitter\.com|x\.com|facebook\.com|fb\.watch)/\S*", re.I)
sem = asyncio.Semaphore(2)  # max 2 heavy jobs at once


def short(s):
    return hashlib.sha1(s.encode()).hexdigest()[:10]


def lang_keyboard():
    codes = list(LANGS)
    rows = []
    for i in range(0, len(codes), 2):
        rows.append([types.InlineKeyboardButton(text=LANGS[c], callback_data=f"lang:{c}")
                     for c in codes[i:i + 2]])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


async def render(uid, src, lang):
    top = (await db.get_pool(uid, src))[:2]
    if not top:
        return t(lang, "empty"), None
    lines = [f"{i+1}. 🎵 {c['title']} - {c['artist']}" for i, c in enumerate(top)]
    rows = [[types.InlineKeyboardButton(text=f"➕ {i+1}", callback_data=f"add:{c['id']}"),
             types.InlineKeyboardButton(text=f"❌ {i+1}", callback_data=f"no:{src}:{c['id']}")]
            for i, c in enumerate(top)]
    text = t(lang, "header") + "\n\n" + "\n".join(lines)
    return text, types.InlineKeyboardMarkup(inline_keyboard=rows)


async def present(m, uid, lang, src, pool):
    await db.save_tracks(pool)
    await db.set_pool(uid, src, pool)
    text, kb = await render(uid, src, lang)
    await m.answer(text, reply_markup=kb)


# ---------- language + welcome ----------
@dp.message(CommandStart())
@dp.message(Command("language"))
async def start(m: types.Message):
    await m.answer(PICK, reply_markup=lang_keyboard())


@dp.callback_query(F.data.startswith("lang:"))
async def pick(q: types.CallbackQuery):
    code = q.data.split(":", 1)[1]
    if code not in LANGS:
        return await q.answer()
    await db.set_lang(q.from_user.id, code)
    await q.message.edit_text(t(code, "welcome"))
    await q.answer()


@dp.message(Command("deleteme"))
async def deleteme(m: types.Message):
    lang = await db.get_lang(m.from_user.id)
    await db.delete_user(m.from_user.id)
    await m.answer(t(lang, "deleted"))


# ---------- link (Instagram / TikTok / YouTube ...) ----------
@dp.message(lambda m: m.text and URL_RE.search(m.text))
async def handle_link(m: types.Message):
    url = URL_RE.search(m.text).group(0)
    uid = m.from_user.id
    lang = await db.get_lang(uid)
    status = await m.answer(t(lang, "wait"))
    async with sem:
        with tempfile.TemporaryDirectory() as d:
            try:
                video, meta = await asyncio.to_thread(download, url, d)
            except Exception:
                logging.exception("download failed")
                return await status.edit_text(t(lang, "fail"))
            audio = os.path.join(d, "a.mp3")
            try:
                await asyncio.to_thread(extract_audio, video, audio)
            except Exception:
                audio = None
            pool = await finder.build_pool(audio, meta)
            await m.answer_video(types.FSInputFile(video))
    await present(m, uid, lang, short(meta["id"]), pool)
    await status.delete()


# ---------- voice / audio / video / video note ----------
@dp.message(F.voice | F.audio | F.video | F.video_note)
async def handle_media(m: types.Message):
    uid = m.from_user.id
    lang = await db.get_lang(uid)
    obj = m.voice or m.audio or m.video or m.video_note
    status = await m.answer(t(lang, "wait"))
    async with sem:
        with tempfile.TemporaryDirectory() as d:
            raw, audio = os.path.join(d, "in"), os.path.join(d, "a.mp3")
            try:  # Telegram lets bots download files up to 20 MB
                await bot.download(obj, destination=raw)
                await asyncio.to_thread(extract_audio, raw, audio)
            except Exception:
                logging.exception("media failed")
                return await status.edit_text(t(lang, "fail"))
            pool = await finder.build_pool(audio, {})
    await present(m, uid, lang, short("m:" + obj.file_unique_id), pool)
    await status.delete()


# ---------- typed text: song/artist name or lyrics ----------
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(m: types.Message):
    uid = m.from_user.id
    lang = await db.get_lang(uid)
    q = m.text.strip()[:200]
    status = await m.answer(t(lang, "wait"))
    pool = await finder.search_text(q)
    await present(m, uid, lang, short("t:" + q.lower()), pool)
    await status.delete()


# ---------- buttons ----------
@dp.callback_query(F.data.startswith("no:"))
async def no(q: types.CallbackQuery):
    _, src, tid = q.data.split(":", 2)
    uid = q.from_user.id
    await db.reject(uid, src, tid)  # never shown again for this post/query
    text, kb = await render(uid, src, await db.get_lang(uid))
    await q.message.edit_text(text, reply_markup=kb)
    await q.answer()


async def notify_playlist_bot(uid, text):
    """Message the user via the 2nd bot. Fails if they never pressed Start there."""
    b = Bot(PLAYLIST_BOT_TOKEN)
    try:
        await b.send_message(uid, text)
        return True
    except Exception:
        return False
    finally:
        await b.session.close()


@dp.callback_query(F.data.startswith("add:"))
async def add(q: types.CallbackQuery):
    uid = q.from_user.id
    lang = await db.get_lang(uid)
    tr = await db.get_track(q.data.split(":", 1)[1])
    if not tr:
        return await q.answer(t(lang, "fail"), show_alert=True)
    await db.add_playlist(uid, tr["id"])
    line = f"{t(lang, 'pl_added')}\n{tr['title']} - {tr['artist']}"
    if await notify_playlist_bot(uid, line):
        await q.answer("✅")
    else:
        await q.answer("✅")
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(
            text=t(lang, "pl_open"),
            url=f"https://t.me/{PLAYLIST_BOT_USERNAME}?start=pl")]])
        await q.message.answer(t(lang, "pl_hint"), reply_markup=kb)


async def main():
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
