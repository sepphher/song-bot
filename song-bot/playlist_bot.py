"""Second bot: each user sees only their own playlist (keyed by Telegram user_id)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart

import db
from config import PLAYLIST_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
bot = Bot(PLAYLIST_BOT_TOKEN)
dp = Dispatcher()


async def show(uid):
    items = await db.get_playlist(uid)
    if not items:
        return "پلی‌لیستت خالیه. از ربات اصلی آهنگ اضافه کن 🎧", None
    lines = [f"{i+1}. {t['title']} - {t['artist']}" for i, t in enumerate(items)]
    rows = [[types.InlineKeyboardButton(text=f"🗑 {i+1}", callback_data=f"rm:{t['id']}")]
            for i, t in enumerate(items)]
    return "🎶 پلی‌لیست شما:\n\n" + "\n".join(lines), types.InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
@dp.message(Command("list"))
async def list_cmd(m: types.Message):
    text, kb = await show(m.from_user.id)
    await m.answer(text, reply_markup=kb)


@dp.message(Command("clear"))
async def clear(m: types.Message):
    await db.clear_playlist(m.from_user.id)
    await m.answer("پلی‌لیست خالی شد.")


@dp.message(Command("deleteme"))
async def deleteme(m: types.Message):
    await db.delete_user(m.from_user.id)
    await m.answer("همه‌ی اطلاعات شما پاک شد ✅")


@dp.callback_query(F.data.startswith("rm:"))
async def remove(q: types.CallbackQuery):
    await db.remove_playlist(q.from_user.id, q.data.split(":", 1)[1])
    text, kb = await show(q.from_user.id)
    await q.message.edit_text(text, reply_markup=kb)
    await q.answer("حذف شد")


async def main():
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
