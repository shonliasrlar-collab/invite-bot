import asyncio
import html
import re
import secrets
import shutil
from collections import defaultdict
from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db
from config import BASE_URL, MUSIC_DIR, THEMES, TIMEZONE, UPLOADS

router = Router()
MAX_PHOTOS = 10
MAX_FILE = 20 * 1024 * 1024  # Telegram Bot API yuklab olish chegarasi
_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

EVENT_TYPES = {
    "toy": ("💍 To'y", "Nikoh to'yi"),
    "tugilgan": ("🎂 Tug'ilgan kun", "Tug'ilgan kun"),
    "yubiley": ("🥂 Yubiley", "Yubiley"),
    "sunnat": ("🌙 Sunnat to'yi", "Sunnat to'yi"),
    "boshqa": ("✨ Boshqa", ""),
}
NAME_PROMPTS = {
    "toy": "Kelin va kuyov ismlarini yozing.\nMasalan: <b>Aziz & Malika</b>",
    "tugilgan": "Tug'ilgan kun egasining ismini yozing.\nMasalan: <b>Sardor</b>",
    "yubiley": "Yubilyarning ismini yozing.\nMasalan: <b>Karima opa</b>",
    "sunnat": "Farzandning ismini yozing.\nMasalan: <b>Muhammad Ali</b>",
    "boshqa": "Ism yoki tashkilotchi nomini yozing.",
}
DEFAULT_TEXT = {
    "toy": "Sizni hayotimizdagi eng quvonchli kunda — nikoh to'yimizda ko'rishdan xursand bo'lamiz. "
           "Tashrifingiz biz uchun katta sharaf.",
    "tugilgan": "Sizni tug'ilgan kunimga taklif qilaman! Birga quvnoq vaqt o'tkazamiz.",
    "yubiley": "Yubiley tantanamizga sizni taklif etamiz. Ishtirokingiz bayramimizni to'ldiradi.",
    "sunnat": "Farzandimizning sunnat to'yiga sizni taklif etamiz. Duolaringiz va tashrifingizni kutamiz.",
    "boshqa": "Sizni tadbirimizga taklif etamiz. Kelishingizni intizor kutamiz.",
}

DATE_RE = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


class Form(StatesGroup):
    etype = State()
    custom_title = State()
    names = State()
    date = State()
    time = State()
    address = State()
    location = State()
    text = State()
    photos = State()
    music = State()
    theme = State()


def skip_kb(what: str, label: str = "⏭ O'tkazib yuborish"):
    kb = InlineKeyboardBuilder()
    kb.button(text=label, callback_data=f"skip:{what}")
    return kb.as_markup()


def presets() -> list[str]:
    return sorted(p.name for p in MUSIC_DIR.glob("*.mp3"))


# ───────────── boshlash / bekor qilish / ro'yxat ─────────────

@router.message(CommandStart())
@router.message(Command("new"))
async def start(m: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder()
    for key, (label, _) in EVENT_TYPES.items():
        kb.button(text=label, callback_data=f"type:{key}")
    kb.adjust(2)
    await m.answer(
        "Assalomu alaykum! 👋\nMen tadbiringiz uchun interaktiv elektron taklifnoma tayyorlayman.\n\n"
        "<b>Tadbir turini tanlang:</b>",
        reply_markup=kb.as_markup(),
    )
    await state.set_state(Form.etype)


@router.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("slug"):
        shutil.rmtree(UPLOADS / data["slug"], ignore_errors=True)
    await state.clear()
    await m.answer("Bekor qilindi. Yangisini boshlash: /new")


@router.message(Command("my"))
async def my_invites(m: Message):
    rows = db.list_by_owner(m.from_user.id)
    if not rows:
        await m.answer("Sizda hali taklifnoma yo'q. Yaratish: /new")
        return
    for slug, d in rows:
        kb = InlineKeyboardBuilder()
        kb.button(text="🗑 O'chirish", callback_data=f"del:{slug}")
        await m.answer(
            f"<b>{html.escape(d['title'])}</b> — {html.escape(d['names'])}\n"
            f"📅 {d['datetime'][:10]}\n{BASE_URL}/invite/{slug}",
            reply_markup=kb.as_markup(),
        )


@router.callback_query(F.data.startswith("del:"))
async def delete_invite(cq: CallbackQuery):
    slug = cq.data.split(":", 1)[1]
    if db.delete(slug, cq.from_user.id):
        shutil.rmtree(UPLOADS / slug, ignore_errors=True)
        await cq.message.edit_text("🗑 Taklifnoma o'chirildi.")
    await cq.answer()


# ───────────── 1. tadbir turi ─────────────

@router.callback_query(Form.etype, F.data.startswith("type:"))
async def pick_type(cq: CallbackQuery, state: FSMContext):
    key = cq.data.split(":", 1)[1]
    if key not in EVENT_TYPES:
        return await cq.answer()
    await state.update_data(slug=db.new_slug(), etype=key, title=EVENT_TYPES[key][1], photos=[])
    await cq.answer()
    if key == "boshqa":
        await state.set_state(Form.custom_title)
        await cq.message.answer("Tadbir nomini yozing.\nMasalan: <b>Bitiruv kechasi</b>")
    else:
        await ask_names(cq.message, state)


@router.message(Form.custom_title, F.text)
async def got_title(m: Message, state: FSMContext):
    await state.update_data(title=m.text.strip()[:60])
    await ask_names(m, state)


# ───────────── 2. ism ─────────────

async def ask_names(m: Message, state: FSMContext):
    key = (await state.get_data())["etype"]
    await state.set_state(Form.names)
    await m.answer(f"👤 {NAME_PROMPTS[key]}")


@router.message(Form.names, F.text)
async def got_names(m: Message, state: FSMContext):
    await state.update_data(names=m.text.strip()[:80])
    await state.set_state(Form.date)
    await m.answer("📅 Tadbir sanasini yozing: <b>KK.OO.YYYY</b>\nMasalan: <b>25.12.2026</b>")


# ───────────── 3. sana ─────────────

@router.message(Form.date, F.text)
async def got_date(m: Message, state: FSMContext):
    match = DATE_RE.match(m.text.strip())
    try:
        d = date(int(match[3]), int(match[2]), int(match[1])) if match else None
    except ValueError:
        d = None
    if not d:
        return await m.answer("Sana noto'g'ri. Shu ko'rinishda yozing: <b>25.12.2026</b>")
    if d < datetime.now(ZoneInfo(TIMEZONE)).date():
        return await m.answer("Bu sana o'tib ketgan. Kelajakdagi sanani yozing.")
    await state.update_data(date=d.isoformat())
    await state.set_state(Form.time)
    await m.answer("⏰ Boshlanish vaqtini yozing: <b>SS:DD</b>\nMasalan: <b>18:00</b>")


# ───────────── 4. vaqt ─────────────

@router.message(Form.time, F.text)
async def got_time(m: Message, state: FSMContext):
    match = TIME_RE.match(m.text.strip())
    if not match or int(match[1]) > 23 or int(match[2]) > 59:
        return await m.answer("Vaqt noto'g'ri. Shu ko'rinishda yozing: <b>18:00</b>")
    await state.update_data(time=f"{int(match[1]):02d}:{match[2]}")
    await state.set_state(Form.address)
    await m.answer("📍 Manzilni yozing.\nMasalan: <b>Toshkent, Chilonzor, «Sharq» to'yxonasi</b>")


# ───────────── 5. manzil + lokatsiya ─────────────

@router.message(Form.address, F.text)
async def got_address(m: Message, state: FSMContext):
    await state.update_data(address=m.text.strip()[:200])
    await state.set_state(Form.location)
    await m.answer(
        "🗺 Xaritadagi aniq joyni yuboring:\n"
        "• 📎 → <b>Joylashuv</b> → kerakli joyni tanlang, yoki\n"
        "• Google / Yandex xarita havolasini yuboring.\n\n"
        "O'tkazib yuborsangiz, xarita tugmasi manzil matni bo'yicha qidiradi.",
        reply_markup=skip_kb("location"),
    )


async def ask_text(m: Message, state: FSMContext):
    await state.set_state(Form.text)
    await m.answer(
        "💌 Taklifnoma matnini yozing.\nO'tkazib yuborsangiz, tadbir turiga mos tayyor matn qo'yiladi.",
        reply_markup=skip_kb("text", "⏭ Tayyor matn"),
    )


@router.message(Form.location, F.location)
async def got_location(m: Message, state: FSMContext):
    await state.update_data(lat=m.location.latitude, lon=m.location.longitude)
    await ask_text(m, state)


@router.message(Form.location, F.text.regexp(r"^https?://\S+$"))
async def got_map_link(m: Message, state: FSMContext):
    await state.update_data(map_url=m.text.strip()[:500])
    await ask_text(m, state)


@router.callback_query(Form.location, F.data == "skip:location")
async def skip_location(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await ask_text(cq.message, state)


# ───────────── 6. matn ─────────────

async def ask_photos(m: Message, state: FSMContext):
    await state.set_state(Form.photos)
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tayyor / rasmsiz davom etish", callback_data="photos:done")
    await m.answer(
        f"📸 Rasmlarni yuboring (ko'pi bilan {MAX_PHOTOS} ta). Hammasini yuborgach, «Tayyor» ni bosing.",
        reply_markup=kb.as_markup(),
    )


@router.message(Form.text, F.text)
async def got_text(m: Message, state: FSMContext):
    await state.update_data(text=m.text.strip()[:800])
    await ask_photos(m, state)


@router.callback_query(Form.text, F.data == "skip:text")
async def skip_text(cq: CallbackQuery, state: FSMContext):
    key = (await state.get_data())["etype"]
    await state.update_data(text=DEFAULT_TEXT[key])
    await cq.answer()
    await ask_photos(cq.message, state)


# ───────────── 7. rasmlar ─────────────

async def save_photo(m: Message, state: FSMContext, file_obj, ext: str):
    async with _locks[m.from_user.id]:  # albom bir vaqtda kelganda ro'yxat buzilmasligi uchun
        data = await state.get_data()
        photos: list[str] = data.get("photos", [])
        if len(photos) >= MAX_PHOTOS:
            return await m.answer(f"Ko'pi bilan {MAX_PHOTOS} ta rasm. «Tayyor» ni bosing.")
        folder = UPLOADS / data["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        name = f"p{secrets.token_hex(4)}{ext}"
        await m.bot.download(file_obj, destination=folder / name)
        photos.append(name)
        await state.update_data(photos=photos)
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Tayyor", callback_data="photos:done")
        await m.answer(f"✅ {len(photos)}/{MAX_PHOTOS} rasm qabul qilindi", reply_markup=kb.as_markup())


@router.message(Form.photos, F.photo)
async def got_photo(m: Message, state: FSMContext):
    await save_photo(m, state, m.photo[-1], ".jpg")


@router.message(Form.photos, F.document.mime_type.in_({"image/jpeg", "image/png", "image/webp"}))
async def got_photo_doc(m: Message, state: FSMContext):
    if m.document.file_size and m.document.file_size > MAX_FILE:
        return await m.answer("Fayl 20 MB dan katta.")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[m.document.mime_type]
    await save_photo(m, state, m.document, ext)


@router.callback_query(Form.photos, F.data == "photos:done")
async def photos_done(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(Form.music)
    kb = InlineKeyboardBuilder()
    for i, name in enumerate(presets()):
        kb.button(text="🎵 " + name.removesuffix(".mp3").replace("_", " ").title(), callback_data=f"music:{i}")
    kb.button(text="⬆️ O'zim yuklayman", callback_data="music:upload")
    kb.button(text="🔇 Musiqasiz", callback_data="music:none")
    kb.adjust(1)
    await cq.message.answer(
        "🎵 Fon musiqasini tanlang yoki o'zingizning audio (mp3) faylingizni yuboring.",
        reply_markup=kb.as_markup(),
    )


# ───────────── 8. musiqa ─────────────

async def ask_theme(m: Message, state: FSMContext):
    await state.set_state(Form.theme)
    kb = InlineKeyboardBuilder()
    show_preview = BASE_URL.startswith("https://")
    for key, label in THEMES.items():
        kb.button(text=label, callback_data=f"theme:{key}")
        if show_preview:
            kb.button(text="👁 Namuna", url=f"{BASE_URL}/preview/{key}")
    kb.adjust(2 if show_preview else 1)
    await m.answer("🎨 Dizaynni tanlang:", reply_markup=kb.as_markup())


@router.callback_query(Form.music, F.data.startswith("music:"))
async def pick_music(cq: CallbackQuery, state: FSMContext):
    choice = cq.data.split(":", 1)[1]
    if choice == "upload":
        await cq.answer()
        return await cq.message.answer("⬆️ Audio faylni (mp3) shu yerga yuboring.")
    if choice == "none":
        await state.update_data(music="")
    else:
        files = presets()
        if not choice.isdigit() or int(choice) >= len(files):
            return await cq.answer("Bu musiqa topilmadi")
        await state.update_data(music=f"/static/music/{quote(files[int(choice)])}")
    await cq.answer()
    await ask_theme(cq.message, state)


@router.message(Form.music, F.audio | F.voice | F.document)
async def got_music(m: Message, state: FSMContext):
    f = m.audio or m.voice or m.document
    if m.document and not (m.document.mime_type or "").startswith("audio/"):
        return await m.answer("Bu audio fayl emas. mp3 yuboring.")
    if f.file_size and f.file_size > MAX_FILE:
        return await m.answer("Fayl 20 MB dan katta. Kichikroq fayl yuboring.")
    if m.voice:
        ext = ".ogg"
    else:
        ext = "." + (getattr(f, "file_name", "") or "x.mp3").rsplit(".", 1)[-1].lower()
        if ext not in {".mp3", ".m4a", ".ogg", ".wav"}:
            ext = ".mp3"
    slug = (await state.get_data())["slug"]
    folder = UPLOADS / slug
    folder.mkdir(parents=True, exist_ok=True)
    await m.bot.download(f, destination=folder / f"music{ext}")
    await state.update_data(music=f"/media/{slug}/music{ext}")
    await m.answer("✅ Musiqa qabul qilindi")
    await ask_theme(m, state)


# ───────────── 9. dizayn va yakun ─────────────

@router.callback_query(Form.theme, F.data.startswith("theme:"))
async def pick_theme(cq: CallbackQuery, state: FSMContext):
    theme = cq.data.split(":", 1)[1]
    if theme not in THEMES:
        return await cq.answer()
    d = await state.get_data()
    slug = d["slug"]
    data = {
        "etype": d["etype"],
        "title": d["title"],
        "names": d["names"],
        "datetime": f"{d['date']}T{d['time']}",
        "address": d["address"],
        "lat": d.get("lat"),
        "lon": d.get("lon"),
        "map_url": d.get("map_url", ""),
        "text": d["text"],
        "photos": d.get("photos", []),
        "music": d.get("music", ""),
        "theme": theme,
    }
    db.save(slug, cq.from_user.id, data)
    await state.clear()
    await cq.answer()

    url = f"{BASE_URL}/invite/{slug}"
    kb = InlineKeyboardBuilder()
    if BASE_URL.startswith("https://"):
        kb.button(text="🔗 Ochib ko'rish", url=url)
    kb.button(text="📤 Mehmonlarga yuborish", url=f"https://t.me/share/url?url={quote(url)}")
    kb.adjust(1)
    await cq.message.answer(
        f"🎉 <b>Taklifnomangiz tayyor!</b>\n\n{url}\n\n"
        "Linkni mehmonlaringizga yuboring. Yangi taklifnoma: /new, mening taklifnomalarim: /my",
        reply_markup=kb.as_markup(),
    )


# ───────────── zaxira javoblar ─────────────

@router.message(StateFilter(None))
async def idle(m: Message):
    await m.answer("Yangi taklifnoma yaratish uchun /new ni bosing.")


@router.message(~StateFilter(None))
async def wrong_input(m: Message):
    await m.answer("Iltimos, so'ralgan ma'lumotni yuboring. Bekor qilish: /cancel")


@router.callback_query()
async def stale_button(cq: CallbackQuery):
    # bot qayta ishga tushganda eski tugmalar shu yerga tushadi
    await cq.answer("Bu tugma eskirgan. Yangi taklifnoma: /new", show_alert=True)
