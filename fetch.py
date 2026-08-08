import re
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import httpx
import feedparser

from config import HTTP_TIMEOUT, HTTP_HEADERS


def clean_summary(raw: str, limit: int = 300) -> str:
    text = re.sub(r"<[^>]+>", "", raw or "").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def parse_date(struct_time) -> Optional[datetime]:
    if not struct_time:
        return None
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


def _guid(entry: Any, link: str, title: str, published: Optional[datetime]) -> str:
    raw = entry.get("id") or entry.get("guid") or link
    if raw:
        return raw
    base = f"{title}|{published.isoformat() if published else ''}"
    return "sha1:" + hashlib.sha1(base.encode("utf-8")).hexdigest()


async def fetch_feed(
    client: httpx.AsyncClient, feed: Dict[str, str]
) -> List[Dict[str, Any]]:
    try:
        resp = await client.get(feed["url"], headers=HTTP_HEADERS,
                                timeout=HTTP_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException):
        return []

    parsed = feedparser.parse(resp.content)

    items: List[Dict[str, Any]] = []
    for entry in parsed.entries:
        link = entry.get("link", "")
        title = entry.get("title", "(sem título)")
        published = parse_date(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        items.append({
            "feed_id": feed["id"],
            "source": feed["name"],
            "category": feed.get("category", "geral"),
            "guid": _guid(entry, link, title, published),
            "title": title,
            "link": link,
            "summary": clean_summary(entry.get("summary", "")),
            "published": published,
        })
    return items


async def fetch_all(feeds: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[fetch_feed(client, f) for f in feeds])
    return [item for sublist in results for item in sublist]
