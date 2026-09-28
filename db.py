import json
import secrets
import sqlite3
import string
from contextlib import closing

from config import DB_PATH

_ALPHABET = string.ascii_lowercase + string.digits


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with closing(_conn()) as c, c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS invitations(
                slug TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_owner ON invitations(owner_id)")


def new_slug() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def save(slug: str, owner_id: int, data: dict) -> None:
    with closing(_conn()) as c, c:
        c.execute(
            "INSERT OR REPLACE INTO invitations(slug, owner_id, data) VALUES (?,?,?)",
            (slug, owner_id, json.dumps(data, ensure_ascii=False)),
        )


def get(slug: str) -> dict | None:
    with closing(_conn()) as c:
        row = c.execute("SELECT data FROM invitations WHERE slug=?", (slug,)).fetchone()
    return json.loads(row["data"]) if row else None


def list_by_owner(owner_id: int) -> list[tuple[str, dict]]:
    with closing(_conn()) as c:
        rows = c.execute(
            "SELECT slug, data FROM invitations WHERE owner_id=? ORDER BY created_at DESC LIMIT 20",
            (owner_id,),
        ).fetchall()
    return [(r["slug"], json.loads(r["data"])) for r in rows]


def delete(slug: str, owner_id: int) -> bool:
    with closing(_conn()) as c, c:
        cur = c.execute("DELETE FROM invitations WHERE slug=? AND owner_id=?", (slug, owner_id))
        return cur.rowcount > 0
