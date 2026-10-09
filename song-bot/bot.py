"""Main bot: Instagram story/post/reel link -> video + song candidates."""
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

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/\S+")
sem = asyncio.Semaphore(2)  # max 2 downloads at once


def short(s):
    return hashlib.sha1(s.encode()).hexdigest()[:10]


async def render(uid, src):
    top = (await db.get_pool(uid, src))[:2]
    if not top:
        return "گزینه‌ی دیگه‌ای برای این مورد نمونده. یه پست/استوری دیگه امتحان کن 🎧", None
    lines = [f"{i+1}. 🎵 {c['title']} - {c['artist']}" for i, c in enumerate(top)]
    rows = [[types.InlineKeyboardButton(text=f"➕ پلی‌لیست {i+1}", callback_data=f"add:{c['id']}"),
             types.InlineKeyboardButton(text=f"❌ {i+1} نیست", callback_data=f"no:{src}:{c['id']}")]
            for i, c in enumerate(top)]
    text = "این آهنگ‌ها نزدیک‌ترین‌ها هستن:\n\n" + "\n".join(lines)
    return text, types.InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
async def start(m: types.Message):
    await m.answer("لینک استوری، پست یا ریلز اینستاگرام رو بفرست 🎬\n"
                   "ویدیو رو می‌گیرم و آهنگش رو پیدا می‌کنم.\n\n"
                   "/deleteme  حذف همه‌ی اطلاعات شما")


@dp.message(Command("deleteme"))
async def deleteme(m: types.Message):
    await db.delete_user(m.from_user.id)
    await m.answer("همه‌ی اطلاعات شما پاک شد ✅")


@dp.message(F.text.regexp(URL_RE))
async def handle(m: types.Message):
    url = URL_RE.search(m.text).group(0)
    uid = m.from_user.id
    status = await m.answer("⏳ در حال دانلود...")
    async with sem:
        with tempfile.TemporaryDirectory() as d:
            try:
                video, meta = await asyncio.to_thread(download, url, d)
            except Exception:
                logging.exception("download failed")
                return await status.edit_text(
                    "دانلود نشد. لینک رو چک کن (محتوای خصوصی قابل دانلود نیست).")
            audio = os.path.join(d, "a.mp3")
            try:
                await asyncio.to_thread(extract_audio, video, audio)
            except Exception:
                audio = None
            src = short(meta["id"])
            pool = await finder.build_pool(audio, meta)
            await db.save_tracks(pool)
            await db.set_pool(uid, src, pool)
            await m.answer_video(types.FSInputFile(video))
    text, kb = await render(uid, src)
    await m.answer(text, reply_markup=kb)
    await status.delete()


@dp.callback_query(F.data.startswith("no:"))
async def no(q: types.CallbackQuery):
    _, src, tid = q.data.split(":", 2)
    await db.reject(q.from_user.id, src, tid)  # never shown again for this post
    text, kb = await render(q.from_user.id, src)
    await q.message.edit_text(text, reply_markup=kb)
    await q.answer()


async def notify_playlist_bot(uid, text):
    """Send to the user via the 2nd bot. Fails if user never pressed Start there."""
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
    t = await db.get_track(q.data.split(":", 1)[1])
    if not t:
        return await q.answer("آهنگ پیدا نشد، دوباره لینک بفرست.", show_alert=True)
    await db.add_playlist(uid, t["id"])
    ok = await notify_playlist_bot(uid, f"✅ به پلی‌لیست اضافه شد:\n{t['title']} - {t['artist']}")
    if ok:
        await q.answer("به پلی‌لیست اضافه شد ✅")
    else:
        await q.answer("اضافه شد ✅")
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(
            text="باز کردن ربات پلی‌لیست",
            url=f"https://t.me/{PLAYLIST_BOT_USERNAME}?start=pl")]])
        await q.message.answer("برای دیدن پلی‌لیست، یک‌بار ربات پلی‌لیست رو Start کن:", reply_markup=kb)


async def main():
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
