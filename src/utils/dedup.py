import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("dedup")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PATH = PROJECT_ROOT / "data" / "seen_articles.json"


def load_seen(path: Path = None) -> dict:
    p = path or DEFAULT_PATH
    try:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"加载去重数据失败: {e}")
    return {}


def save_seen(data: dict, path: Path = None):
    p = path or DEFAULT_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存去重数据失败: {e}")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def filter_unseen(articles: list[dict], seen_data: dict) -> list[dict]:
    seen_hashes = set(seen_data.keys())
    unseen = []
    for a in articles:
        h = url_hash(a.get("url", ""))
        if h not in seen_hashes:
            unseen.append(a)
    logger.info(f"去重: {len(articles)} 篇 → {len(unseen)} 篇新文章")
    return unseen


def mark_seen(articles: list[dict], seen_data: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    for a in articles:
        h = url_hash(a.get("url", ""))
        seen_data[h] = today
    return seen_data


def cleanup_old(seen_data: dict, retention_days: int = 7) -> dict:
    cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    cleaned = {h: d for h, d in seen_data.items() if d >= cutoff}
    removed = len(seen_data) - len(cleaned)
    if removed > 0:
        logger.info(f"清理过期去重记录: {removed} 条")
    return cleaned
