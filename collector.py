import asyncio
import logging

import config
import db
from feeds import load_feeds
from fetch import fetch_all

log = logging.getLogger("news_mcp.collector")


async def poll_once() -> int:
    feeds = load_feeds()
    articles = await fetch_all(feeds)
    inserted = await asyncio.to_thread(db.upsert_articles, articles)
    removed = await asyncio.to_thread(db.prune, config.RETENTION_DAYS)
    log.info("coleta: %d feeds, %d artigos baixados, %d novos, %d podados",
             len(feeds), len(articles), inserted, removed)
    return inserted


async def run_collector() -> None:
    while True:
        try:
            await poll_once()
        except Exception:
            log.exception("falha na coleta; tentando de novo no próximo ciclo")
        await asyncio.sleep(config.POLL_INTERVAL_MIN * 60)
