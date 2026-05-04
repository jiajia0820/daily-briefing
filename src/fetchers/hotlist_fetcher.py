import time
from datetime import datetime, timezone

import requests

from src.utils.logger import get_logger

logger = get_logger("hotlist_fetcher")

DEFAULT_API_URL = "https://newsnow.busiyi.world/api/s"
TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DailyBriefing/1.0",
    "Accept": "application/json, text/plain, */*",
}


def fetch_hotlists(
    sources: list[dict],
    api_url: str = "",
    count_per_source: int = 10,
    request_interval_ms: int = 500,
) -> list[dict]:
    articles = []
    base_url = (api_url or DEFAULT_API_URL).rstrip("/")

    for index, source in enumerate(sources):
        source_id = source.get("id", "").strip()
        source_name = source.get("name", source_id).strip()
        if not source_id:
            continue

        try:
            logger.info(f"{source_name}: 正在抓取热榜")
            resp = requests.get(
                base_url,
                params={"id": source_id, "latest": ""},
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")
            if status not in ("success", "cache"):
                logger.warning(f"{source_name}: 热榜状态异常 ({status})，已跳过")
                continue

            updated_at = _parse_updated_time(data.get("updatedTime"))
            items = data.get("items", [])[:count_per_source]
            for rank, item in enumerate(items, 1):
                title = str(item.get("title", "")).strip()
                url = item.get("url") or item.get("mobileUrl") or ""
                url = str(url).strip()
                if not title or not url:
                    continue
                articles.append({
                    "title": title,
                    "url": url,
                    "source": f"全网热榜 · {source_name}",
                    "category": "全网热榜",
                    "platform_id": source_id,
                    "rank": rank,
                    "published_at": updated_at,
                })
            logger.info(f"{source_name}: 获取 {len(items)} 条热榜")
        except requests.exceptions.Timeout:
            logger.warning(f"{source_name}: 热榜请求超时，已跳过")
        except requests.exceptions.RequestException as e:
            logger.warning(f"{source_name}: 热榜请求失败 ({e})，已跳过")
        except Exception as e:
            logger.warning(f"{source_name}: 热榜解析失败 ({e})，已跳过")

        if index < len(sources) - 1 and request_interval_ms > 0:
            time.sleep(request_interval_ms / 1000)

    logger.info(f"热榜抓取完成，共 {len(articles)} 条")
    return articles


def split_articles_by_keywords(
    articles: list[dict],
    keywords: list[str],
) -> tuple[list[dict], list[dict]]:
    normalized_keywords = [kw.lower() for kw in keywords if kw]
    matched = []
    unmatched = []
    for article in articles:
        title = article.get("title", "").lower()
        if normalized_keywords and any(kw in title for kw in normalized_keywords):
            matched.append(article)
        else:
            unmatched.append(article)
    return matched, unmatched


def _parse_updated_time(value) -> str:
    try:
        if value:
            return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()
