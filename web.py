import re
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
from config import BASE_URL, ROOT, TIMEZONE, UPLOADS
from palettes import PALETTES, PATTERNS, normalize_hex, resolve

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/media", StaticFiles(directory=UPLOADS), name="media")
templates = Jinja2Templates(directory=ROOT / "templates")

MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
          "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]


def build_view(slug: str, d: dict) -> dict:
    when = datetime.fromisoformat(d["datetime"]).replace(tzinfo=ZoneInfo(TIMEZONE))
    names = d.get("names", "")
    parts = [p for p in re.split(r"\s*&\s*|\s+va\s+", names, maxsplit=1) if p]

    address = d.get("address", "")
    lat, lon = d.get("lat"), d.get("lon")
    map_url = d.get("map_url") or ""
    if not map_url.startswith(("http://", "https://")):
        map_url = ""
    q = quote(address)
    if map_url:
        view_url = map_url
    elif lat is not None:
        view_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    else:
        view_url = f"https://www.google.com/maps/search/?api=1&query={q}"
    dest = f"{lat},{lon}" if lat is not None else q
    route_url = f"https://www.google.com/maps/dir/?api=1&destination={dest}"
    yandex_url = f"https://yandex.com/maps/?pt={lon},{lat}&z=16&l=map" if lat is not None else ""

    photos = [f"/media/{slug}/{p}" for p in d.get("photos", [])]
    css_vars, bg = resolve(d)
    cover = d.get("cover")
    return {
        "slug": slug,
        "title": d.get("title", ""),
        "names": names,
        "name_parts": parts if len(parts) == 2 else [names],
        "date_text": f"{when.day} {MONTHS[when.month - 1]} {when.year}",
        "weekday": WEEKDAYS[when.weekday()],
        "time_text": when.strftime("%H:%M"),
        "target_iso": when.isoformat(),
        "address": address,
        "text": d.get("text", ""),
        "photos": photos,
        "og_image": f"{BASE_URL}{photos[0]}" if photos else "",
        "music": d.get("music") or "",
        "css_vars": css_vars,
        "bg": bg,
        "cover": f"/media/{slug}/{cover}" if cover else "",
        "view_url": view_url,
        "route_url": route_url,
        "yandex_url": yandex_url,
        "url": f"{BASE_URL}/invite/{slug}",
    }


def render(request: Request, slug: str, data: dict):
    return templates.TemplateResponse(request, "invite.html", {"v": build_view(slug, data)})


@app.get("/", response_class=PlainTextResponse)
def home():
    return "Elektron taklifnoma xizmati"


@app.get("/invite/{slug}")
def invite(request: Request, slug: str):
    data = db.get(slug)
    if not data:
        raise HTTPException(404, "Taklifnoma topilmadi")
    return render(request, slug, data)


@app.get("/preview/{theme}")
def preview(request: Request, theme: str, pattern: str = "xatam", bg: str = "", accent: str = ""):
    if pattern not in PATTERNS:
        pattern = "xatam"
    if theme == "custom":
        bg, accent = normalize_hex(bg), normalize_hex(accent)
        if not (bg and accent):
            raise HTTPException(404)
    elif theme not in PALETTES:
        raise HTTPException(404)
    when = (datetime.now(ZoneInfo(TIMEZONE)) + timedelta(days=30)).replace(
        hour=18, minute=0, second=0, microsecond=0, tzinfo=None
    )
    demo = {
        "title": "Nikoh to'yi",
        "names": "Aziz & Malika",
        "datetime": when.isoformat(timespec="minutes"),
        "address": "Toshkent, Chilonzor tumani, «Sharq» to'yxonasi",
        "lat": 41.2856, "lon": 69.2038,
        "text": "Sizni hayotimizdagi eng quvonchli kunda — nikoh to'yimizda ko'rishdan xursand bo'lamiz. "
                "Tashrifingiz biz uchun katta sharaf.",
        "palette": theme, "bg": bg, "accent": accent, "pattern": pattern,
    }
    return render(request, "demo", demo)
