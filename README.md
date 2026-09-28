# Telegram elektron taklifnoma boti

Bot + veb-sayt bitta jarayonda ishlaydi (aiogram 3 + FastAPI + SQLite).

## Ishga tushirish
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # BOT_TOKEN va BASE_URL ni yozing
python main.py
```
Bot Telegramdan yangilarni oladi, sayt esa `PORT` (standart 8000) da ishlaydi.

## Test qilish (kompyuterda)
`cloudflared tunnel --url http://localhost:8000` yoki `ngrok http 8000` bilan https manzil oling
va uni `.env` dagi `BASE_URL` ga yozing. Namuna dizaynlar: `BASE_URL/preview/oltin`, `/lola`, `/kecha`, `/rangli`.

## Serverga joylash
1. VPS + domen; Caddy yoki Nginx orqali HTTPS ni `localhost:8000` ga yo'naltiring.
2. `python main.py` ni systemd yoki Docker bilan doimiy ishlating.
3. `uploads/` va `data.db` ni muntazam zaxiralang.

## Fon musiqa
`static/music/` ga `.mp3` fayllar joylang, bot ularni tugma sifatida ko'rsatadi.
Foydalanuvchi o'z audiosini ham yuklashi mumkin (Telegram cheklovi: 20 MB gacha).

## Bot buyruqlari
`/new` yangi taklifnoma, `/my` mening taklifnomalarim (o'chirish bilan), `/cancel` bekor qilish.

## Keyingi qadamlar
Mehmonlar javobi (kelaman/kelmayman), to'lov, Postgres + S3, webhook rejimi, admin panel.
