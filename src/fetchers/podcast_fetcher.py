import json
import requests
import feedparser
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("podcast_fetcher")

TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "podcast_history.json"

# Apple Podcasts 科技类单集热榜（中国区）
APPLE_EPISODES_URL = "https://rss.marketingtools.apple.com/api/v2/cn/podcasts/top/25/podcast-episodes.json"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"

# 感兴趣的分类 genre id（Apple Podcasts）
# 1318=科技  1321=商务  1304=教育  1489=新闻
GENRE_IDS = ["1318", "1321", "1304", "1489"]


def _fetch_apple_trending(count: int = 20) -> list[dict]:
    all_eps = []
    seen_ids = set()
    for genre in GENRE_IDS:
        try:
            resp = requests.get(
                APPLE_EPISODES_URL,
                params={"genre": genre},
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json().get("feed", {}).get("results", [])
            for item in results:
                ep_id = str(item.get("id", ""))
                if ep_id and ep_id not in seen_ids:
                    seen_ids.add(ep_id)
                    all_eps.append({
                        "ep_name": item.get("name", ""),
                        "artist": item.get("artistName", ""),
                        "apple_url": item.get("url", ""),
                        "ep_id": ep_id,
                    })
        except Exception as e:
            logger.warning(f"Apple Podcasts genre={genre} 抓取失败: {e}")
    logger.info(f"Apple Podcasts 热榜: 获取 {len(all_eps)} 条单集")
    return all_eps[:count]


def _load_history() -> list[str]:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(ep_id: str):
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        history = _load_history()
        history.append(ep_id)
        history = history[-100:]
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存播客推荐历史失败: {e}")


def fetch_podcast(sources: list[dict] = None) -> dict | None:
    # 从 Apple Podcasts 热榜发现
    episodes = _fetch_apple_trending(count=25)
    if not episodes:
        logger.warning("Apple Podcasts 热榜为空")
        return None

    # 去重已推荐
    history = set(_load_history())
    unseen = [ep for ep in episodes if ep.get("ep_id") not in history]

    if not unseen:
        logger.info("所有热榜单集均已推荐过，重置历史")
        unseen = episodes
        try:
            HISTORY_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    pick = unseen[0]
    _save_history(pick.get("ep_id", ""))
    logger.info(f"播客推荐: {pick['artist']} · {pick['ep_name']}")
    return {
        "name": pick["artist"],
        "episode_title": pick["ep_name"],
        "url": pick["apple_url"],
        "platform": "apple_podcasts",
    }
