import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  feed_id    TEXT NOT NULL,
  source     TEXT NOT NULL,
  category   TEXT NOT NULL,
  guid       TEXT NOT NULL,
  title      TEXT NOT NULL,
  link       TEXT,
  summary    TEXT,
  published  TEXT,
  fetched_at TEXT NOT NULL,
  UNIQUE(feed_id, guid)
);
CREATE INDEX IF NOT EXISTS idx_cat_pub ON articles(category, published DESC);
CREATE INDEX IF NOT EXISTS idx_pub     ON articles(published DESC);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _from_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def upsert_articles(articles: List[Dict[str, Any]]) -> int:
    if not articles:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (a["feed_id"], a["source"], a["category"], a["guid"], a["title"],
         a.get("link"), a.get("summary"), _iso(a.get("published")), now)
        for a in articles
    ]
    with _connect() as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO articles "
            "(feed_id, source, category, guid, title, link, summary, published, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        return conn.total_changes - before


def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
    return [
        {
            "source": r["source"],
            "category": r["category"],
            "title": r["title"],
            "link": r["link"],
            "summary": r["summary"],
            "published": _from_iso(r["published"]),
        }
        for r in rows
    ]


_ORDER = " ORDER BY published IS NULL, published DESC LIMIT ?"


def latest(category: Optional[str], source_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM articles"
    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if source_id:
        where.append("feed_id = ?")
        params.append(source_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += _ORDER
    params.append(limit)
    with _connect() as conn:
        return _rows_to_dicts(conn.execute(sql, params).fetchall())


def search(keyword: str, category: Optional[str], limit: int) -> List[Dict[str, Any]]:
    like = f"%{keyword}%"
    sql = "SELECT * FROM articles WHERE (title LIKE ? OR summary LIKE ?)"
    params: List[Any] = [like, like]
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += _ORDER
    params.append(limit)
    with _connect() as conn:
        return _rows_to_dicts(conn.execute(sql, params).fetchall())


def prune(days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        before = conn.total_changes
        conn.execute("DELETE FROM articles WHERE fetched_at < ?", (cutoff,))
        return conn.total_changes - before


def stats() -> Dict[str, Any]:
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        by_cat = conn.execute(
            "SELECT category, COUNT(*) AS c FROM articles GROUP BY category ORDER BY category"
        ).fetchall()
        last = conn.execute("SELECT MAX(fetched_at) FROM articles").fetchone()[0]
    return {
        "total": total,
        "by_category": {r["category"]: r["c"] for r in by_cat},
        "last_fetch": last,
    }
