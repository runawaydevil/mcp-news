import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

import config
import db
from feeds import load_feeds, categories, filter_category
from formatting import format_items
from models import LatestInput, SearchInput
from collector import run_collector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("news_mcp")


@asynccontextmanager
async def lifespan(_server: FastMCP):
    db.init_db()
    task = asyncio.create_task(run_collector())
    log.info("news_mcp no ar; coletor rodando a cada %d min", config.POLL_INTERVAL_MIN)
    try:
        yield
    finally:
        task.cancel()


mcp = FastMCP("news_mcp", lifespan=lifespan)


@mcp.tool(
    name="list_sources",
    annotations={"title": "List configured news sources",
                 "readOnlyHint": True, "openWorldHint": False},
)
async def list_sources() -> str:
    """List all RSS news sources configured, grouped by category.

    Returns each source's id (used for filtering) and display name, plus the
    category names usable in the `category` parameter of the other tools.
    """
    feeds = load_feeds()
    if not feeds:
        return "Nenhum feed configurado. Edite o feeds.json e adicione fontes."

    linhas = []
    for cat in categories(feeds):
        do_grupo = [f for f in feeds if f.get("category", "geral") == cat]
        linhas.append(f"## {cat} ({len(do_grupo)} fontes)")
        linhas.extend(f"- {f['name']} (id: `{f['id']}`)" for f in do_grupo)
        linhas.append("")
    return "\n".join(linhas).strip()


@mcp.tool(
    name="get_latest_news",
    annotations={"title": "Get latest news", "readOnlyHint": True, "openWorldHint": True},
)
async def get_latest_news(params: LatestInput) -> str:
    """Get the most recent news articles collected from the RSS feeds.

    Reads from the local store (updated in the background), optionally filtered
    by category and/or a single source_id, newest first, up to `limit`.
    """
    feeds = load_feeds()

    _, erro = filter_category(feeds, params.category)
    if erro:
        return erro

    if params.source_id and not any(f["id"] == params.source_id for f in feeds):
        return (f"Fonte '{params.source_id}' não existe. "
                f"Use list_sources para ver as disponíveis.")

    items = await asyncio.to_thread(
        db.latest, params.category, params.source_id, params.limit
    )
    return format_items(items)


@mcp.tool(
    name="search_news",
    annotations={"title": "Search news by keyword", "readOnlyHint": True, "openWorldHint": True},
)
async def search_news(params: SearchInput) -> str:
    """Search the collected news for a keyword.

    Matches the keyword (case-insensitive) in the article title or summary,
    optionally restricted to one category, newest first, up to `limit`. Because
    it reads history, it can find articles older than the feeds' current window.
    """
    _, erro = filter_category(load_feeds(), params.category)
    if erro:
        return erro

    items = await asyncio.to_thread(
        db.search, params.keyword, params.category, params.limit
    )
    if not items:
        return f"Nada encontrado para '{params.keyword}'."
    return format_items(items)


@mcp.tool(
    name="get_stats",
    annotations={"title": "News store statistics",
                 "readOnlyHint": True, "openWorldHint": False},
)
async def get_stats() -> str:
    """Show how many articles are stored, the breakdown by category, and when
    the last background collection ran. Useful to check the server is healthy.
    """
    s = await asyncio.to_thread(db.stats)
    por_cat = "\n".join(f"- {cat}: {n}" for cat, n in s["by_category"].items())
    return (
        f"**Total de artigos:** {s['total']}\n"
        f"**Última coleta:** {s['last_fetch'] or 'ainda não coletou'}\n\n"
        f"**Por categoria:**\n{por_cat or '- (vazio)'}"
    )


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str):
        super().__init__(app)
        self._expected = f"Bearer {token}" if token else ""

    async def dispatch(self, request: Request, call_next):
        if self._expected and request.headers.get("authorization") != self._expected:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def main() -> None:
    if not config.TOKEN:
        log.warning("NEWS_MCP_TOKEN vazio: servidor SEM autenticação (ok só em dev local).")
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=config.TOKEN)
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")


if __name__ == "__main__":
    main()
