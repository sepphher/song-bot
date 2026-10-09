"""Second bot: each user sees only their own playlist (keyed by Telegram user_id).
Language is shared with the main bot through the same database."""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart

import db
from config import PLAYLIST_BOT_TOKEN
from i18n import t

logging.basicConfig(level=logging.INFO)
bot = Bot(PLAYLIST_BOT_TOKEN)
dp = Dispatcher()


async def show(uid):
    lang = await db.get_lang(uid)
    items = await db.get_playlist(uid)
    if not items:
        return t(lang, "pl_empty"), None
    lines = [f"{i+1}. {x['title']} - {x['artist']}" for i, x in enumerate(items)]
    rows = [[types.InlineKeyboardButton(text=f"🗑 {i+1}", callback_data=f"rm:{x['id']}")]
            for i, x in enumerate(items)]
    return t(lang, "pl_title") + "\n\n" + "\n".join(lines), types.InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
@dp.message(Command("list"))
async def list_cmd(m: types.Message):
    text, kb = await show(m.from_user.id)
    await m.answer(text, reply_markup=kb)


@dp.message(Command("clear"))
async def clear(m: types.Message):
    await db.clear_playlist(m.from_user.id)
    await m.answer(t(await db.get_lang(m.from_user.id), "pl_cleared"))


@dp.message(Command("deleteme"))
async def deleteme(m: types.Message):
    lang = await db.get_lang(m.from_user.id)
    await db.delete_user(m.from_user.id)
    await m.answer(t(lang, "deleted"))


@dp.callback_query(F.data.startswith("rm:"))
async def remove(q: types.CallbackQuery):
    await db.remove_playlist(q.from_user.id, q.data.split(":", 1)[1])
    text, kb = await show(q.from_user.id)
    await q.message.edit_text(text, reply_markup=kb)
    await q.answer(t(await db.get_lang(q.from_user.id), "removed"))


async def main():
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
