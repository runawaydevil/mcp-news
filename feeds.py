import json
from typing import Optional, List, Dict, Tuple

from config import FEEDS_PATH


def load_feeds() -> List[Dict[str, str]]:
    if not FEEDS_PATH.exists():
        return []
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    return data.get("feeds", [])


def categories(feeds: List[Dict[str, str]]) -> List[str]:
    return sorted({f.get("category", "geral") for f in feeds})


def filter_category(
    feeds: List[Dict[str, str]], category: Optional[str]
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    if not category:
        return feeds, None
    cat = category.strip().lower()
    subset = [f for f in feeds if f.get("category", "geral") == cat]
    if not subset:
        validas = ", ".join(categories(feeds))
        return [], f"Categoria '{category}' não existe. Disponíveis: {validas}."
    return subset, None
