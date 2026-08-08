from datetime import datetime, timezone
from typing import List, Dict, Any

_MIN = datetime.min.replace(tzinfo=timezone.utc)


def sort_by_date(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(items, key=lambda x: x.get("published") or _MIN, reverse=True)


def format_items(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "Nenhuma notícia encontrada."
    linhas = []
    for it in items:
        pub = it.get("published")
        data = pub.strftime("%d/%m %H:%M") if pub else "s/ data"
        linhas.append(
            f"### {it['title']}\n"
            f"**{it['source']}** · {data}\n"
            f"{it.get('summary', '')}\n"
            f"{it.get('link', '')}"
        )
    return "\n\n".join(linhas)
