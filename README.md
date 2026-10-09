# Song Finder Bot (Instagram → video + song)

دو ربات تلگرام:
- **bot.py** : لینک استوری/پست/ریلز اینستاگرام → دانلود ویدیو + ۲ آهنگ نزدیک. دکمه‌ی ❌ آهنگ رو برای همون پست دیگه نشون نمیده.
- **playlist_bot.py** : پلی‌لیست شخصی هر کاربر (با user_id تلگرام جدا میشه).

هر دو ربات یک دیتابیس SQLite روی دیسک رو به اشتراک می‌گذارن، پس با خاموش/روشن شدن سرور اطلاعات می‌مونه.

## نصب (Termux)
```bash
pkg install python ffmpeg python-cryptography
pip install -r requirements.txt
cp .env.example .env   # توکن‌ها رو پر کن
python tools.py genkey # دو بار بزن: COOKIES_KEY و BACKUP_KEY
```

## اجرا
```bash
python bot.py &
python playlist_bot.py &
```

## کوکی اینستاگرام (برای استوری)
از اکانت **جدا** (نه اکانت اصلی) cookies.txt بگیر، بعد:
```bash
python tools.py encrypt cookies.txt && rm cookies.txt
```

## بکاپ
`python backup.py` (با cron روزانه). فایل رمز شده به BACKUP_CHAT_ID فرستاده میشه.

## امنیت
- `.env`, `data/`, کوکی‌ها در `.gitignore` هستن؛ هرگز کامیت نکن.
- کوکی‌ها با Fernet رمز میشن، ویدیوها بعد ارسال پاک میشن.
- `/deleteme` همه‌ی اطلاعات کاربر رو پاک می‌کنه.

## محدودیت‌ها
- پست‌های فقط-عکس صدا ندارن و yt-dlp ممکنه پشتیبانی نکنه.
- محتوای خصوصی دانلود نمیشه؛ اینستاگرام ممکنه محدودیت بذاره.
- فقط برای محتوای خود کاربر یا با اجازه استفاده بشه.
