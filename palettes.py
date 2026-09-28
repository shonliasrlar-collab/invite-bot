"""Ranglar palitrasi, naqshlar va avtomatik rang hisoblash (bot ham, sayt ham foydalanadi)."""
import re
from urllib.parse import quote

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")

# kalit: (nomi, fon rangi, urg'u rangi)
PALETTES = {
    "oltin": ("🌿 Zumrad va oltin", "#0F3B37", "#D6B25E"),
    "lola": ("🌷 Lola", "#FBF0EF", "#B0214A"),
    "kecha": ("🌙 Kechasi", "#111838", "#9DBBFF"),
    "rangli": ("🎈 Rangli", "#EAF5FF", "#F0407F"),
    "bordo": ("🍷 Bordo va oltin", "#4A0F27", "#E3B86B"),
    "binafsha": ("💜 Binafsha", "#2B1946", "#F0B8FF"),
    "pista": ("🍃 Pista", "#E8F3EA", "#2F7D5B"),
    "qora": ("🖤 Qora va kumush", "#15151A", "#C9D1DC"),
}

BG_COLORS = [
    ("🟢 Zumrad", "#0F3B37"), ("🔵 Tungi ko'k", "#111838"), ("🟣 Binafsha", "#2B1946"),
    ("🔴 Bordo", "#4A0F27"), ("⚫ Qora", "#15151A"), ("⚪ Oq", "#FFFFFF"),
    ("🌸 Pushti", "#FBE4EC"), ("🩵 Havorang", "#E4F2FF"), ("🍃 Och yashil", "#E8F3EA"),
    ("🟡 Och sariq", "#FFF3CF"),
]
ACCENT_COLORS = [
    ("🟡 Oltin", "#D6B25E"), ("🌹 Qizil", "#C2264D"), ("🩷 Pushti", "#F0407F"),
    ("🔷 Moviy", "#3E7BFA"), ("🟢 Yashil", "#2FA36B"), ("🟠 Zarg'aldoq", "#F28C28"),
    ("🟣 Binafsha", "#8B5CF6"), ("⚪ Kumush", "#C9D1DC"),
]

# kalit: (nomi, plitka o'lchami, SVG ichki qismi)
PATTERNS = {
    "xatam": ("✴️ Xatam (yulduz)", 60,
              "<rect x='12' y='12' width='36' height='36'/>"
              "<polygon points='30,4.5 55.5,30 30,55.5 4.5,30'/><circle cx='30' cy='30' r='3'/>"),
    "romb": ("🔷 Romb to'ri", 40,
             "<polygon points='20,2 38,20 20,38 2,20'/><polygon points='20,10 30,20 20,30 10,20'/>"),
    "gul": ("🌸 Gul", 64,
            "<g transform='translate(32 32)'><ellipse cx='0' cy='-12' rx='6' ry='12'/>"
            "<ellipse cx='0' cy='-12' rx='6' ry='12' transform='rotate(90)'/>"
            "<ellipse cx='0' cy='-12' rx='6' ry='12' transform='rotate(180)'/>"
            "<ellipse cx='0' cy='-12' rx='6' ry='12' transform='rotate(270)'/><circle r='3'/></g>"),
    "tolqin": ("🌊 To'lqin", 48,
               "<path d='M0 24 Q12 8 24 24 T48 24'/><path d='M0 44 Q12 28 24 44 T48 44'/>"),
    "nuqta": ("⚫ Nuqtalar", 28, "<circle cx='14' cy='14' r='2' fill='black' stroke='none'/>"),
    "chiziq": ("▨ Chiziqlar", 24, "<path d='M0 24 L24 0 M-6 6 L6 -6 M18 30 L30 18'/>"),
    "yoq": ("🚫 Naqshsiz", 0, ""),
}

LIGHT_INK = (246, 241, 228)
DARK_INK = (30, 22, 32)


def normalize_hex(s: str | None) -> str | None:
    m = _HEX.match((s or "").strip())
    return "#" + m.group(1).upper() if m else None


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x))) for x in c)


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(c) -> float:
    r, g, b = (_lin(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def derive(bg_hex: str, accent_hex: str) -> dict:
    """Ikkita rangdan o'qiladigan (kontrastli) to'liq palitra hosil qiladi."""
    bg, ac = _rgb(bg_hex), _rgb(accent_hex)
    dark = _contrast(bg, LIGHT_INK) > _contrast(bg, DARK_INK)
    ink = LIGHT_INK if dark else DARK_INK

    t = 0.0  # urg'u rangi fonda ko'rinmay qolmasligi uchun matn rangi tomon suramiz
    adj = ac
    while _contrast(adj, bg) < 3 and t < 1:
        t += 0.12
        adj = _mix(ac, ink, t)

    black, white = (0, 0, 0), (255, 255, 255)
    if dark:
        door, door_ink, door_acc = _mix(bg, black, 0.3), ink, adj
        bg2 = _mix(bg, black, 0.22)
    else:
        door, door_ink, door_acc = _mix(adj, black, 0.6), bg, _mix(adj, white, 0.55)
        bg2 = _mix(bg, black, 0.06)
    on_acc = white if _contrast(adj, white) >= _contrast(adj, (16, 16, 20)) else (16, 16, 20)
    return {
        "bg": _hex(bg), "bg2": _hex(bg2), "ink": _hex(ink), "muted": _hex(_mix(ink, bg, 0.4)),
        "accent": _hex(adj), "door": _hex(door), "door-ink": _hex(door_ink),
        "door-accent": _hex(door_acc), "on-accent": _hex(on_acc),
    }


def pattern_url(key: str) -> tuple[str, int]:
    _, size, inner = PATTERNS.get(key, PATTERNS["xatam"])
    if not size:
        return "none", 60
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
           f"viewBox='0 0 {size} {size}'><g fill='none' stroke='black' stroke-width='1.2'>{inner}</g></svg>")
    return f"url(data:image/svg+xml,{quote(svg, safe='')})", size


def resolve(d: dict) -> tuple[str, str]:
    """Bazadagi ma'lumotdan (css o'zgaruvchilari, fon rangi) qaytaradi."""
    key = d.get("palette") or d.get("theme") or "oltin"
    if key in PALETTES:
        _, bg, ac = PALETTES[key]
    else:
        bg = normalize_hex(d.get("bg")) or PALETTES["oltin"][1]
        ac = normalize_hex(d.get("accent")) or PALETTES["oltin"][2]
    pat = d.get("pattern") if d.get("pattern") in PATTERNS else "xatam"
    vars_ = derive(bg, ac)
    tile, size = pattern_url(pat)
    vars_["tile"], vars_["tile-size"] = tile, f"{size}px"
    vars_["pat-op"] = "0" if pat == "yoq" else ".16"
    return ";".join(f"--{k}:{v}" for k, v in vars_.items()), vars_["bg"]
