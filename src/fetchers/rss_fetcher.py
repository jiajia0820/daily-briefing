import feedparser
import requests
from datetime import datetime, timezone
from src.utils.logger import get_logger

logger = get_logger("rss_fetcher")

TIMEOUT = 10


def fetch_rss(sources: list[dict]) -> list[dict]:
    all_articles = []
    for source in sources:
        name = source.get("name", "unknown")
        url = source.get("url", "")
        category = source.get("category", "")
        try:
            logger.info(f"{name}: 正在抓取 {url}")
            resp = requests.get(url, timeout=TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DailyBriefing/1.0"
            })
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            entries = feed.entries or []
            logger.info(f"{name}: 获取 {len(entries)} 篇文章")
            for entry in entries:
                article = {
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", "").strip(),
                    "source": name,
                    "category": category,
                    "published_at": _parse_date(entry),
                }
                if article["title"] and article["url"]:
                    all_articles.append(article)
        except requests.exceptions.Timeout:
            logger.warning(f"{name}: 请求超时，已跳过")
        except requests.exceptions.RequestException as e:
            logger.warning(f"{name}: 请求失败 ({e})，已跳过")
        except Exception as e:
            logger.warning(f"{name}: 解析失败 ({e})，已跳过")
    logger.info(f"RSS 抓取完成，共 {len(all_articles)} 篇文章")
    return all_articles


def _parse_date(entry) -> str:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        try:
            dt = datetime(*published[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()
