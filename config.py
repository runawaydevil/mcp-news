import os
from pathlib import Path

_BASE = Path(__file__).parent

HTTP_TIMEOUT = 10
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (news-mcp)"}

FEEDS_PATH = Path(os.environ.get("FEEDS_PATH", _BASE / "feeds.json"))
DB_PATH = Path(os.environ.get("DB_PATH", _BASE / "news.db"))

HOST = os.environ.get("NEWS_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("NEWS_MCP_PORT", "17631"))
TOKEN = os.environ.get("NEWS_MCP_TOKEN", "")

POLL_INTERVAL_MIN = int(os.environ.get("POLL_INTERVAL_MIN", "30"))
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))
