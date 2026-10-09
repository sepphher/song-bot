"""Encrypted DB backup sent to a private Telegram chat/channel.
Run from cron, e.g. daily:  python backup.py"""
import asyncio
import datetime
import os
import sqlite3
import tempfile

from aiogram import Bot, types
from cryptography.fernet import Fernet
from config import BACKUP_CHAT_ID, BACKUP_KEY, BOT_TOKEN, DB_PATH


async def main():
    with tempfile.TemporaryDirectory() as d:
        copy = os.path.join(d, "copy.db")
        src, dst = sqlite3.connect(DB_PATH), sqlite3.connect(copy)
        src.backup(dst)  # consistent snapshot even while bots are running
        src.close(); dst.close()
        with open(copy, "rb") as f:
            enc = Fernet(BACKUP_KEY.encode()).encrypt(f.read())
        out = os.path.join(d, f"backup-{datetime.date.today()}.db.enc")
        with open(out, "wb") as f:
            f.write(enc)
        bot = Bot(BOT_TOKEN)
        await bot.send_document(int(BACKUP_CHAT_ID), types.FSInputFile(out))
        await bot.session.close()

asyncio.run(main())
