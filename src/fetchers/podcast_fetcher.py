import feedparser
import requests
from src.utils.logger import get_logger

logger = get_logger("podcast_fetcher")

TIMEOUT = 10


def fetch_podcast(sources: list[dict]) -> dict | None:
    for source in sources:
        name = source.get("name", "unknown")
        url = source.get("url", "")
        platform = source.get("platform", "")
        try:
            logger.info(f"播客 {name}: 正在抓取 {url}")
            resp = requests.get(url, timeout=TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0 DailyBriefing/1.0"
            })
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            entries = feed.entries or []
            if entries:
                latest = entries[0]
                episode_title = latest.get("title", "").strip()
                episode_url = latest.get("link", "").strip()

                # 尝试构建小宇宙链接
                if platform == "xiaoyuzhoufm" and episode_url:
                    pass  # 保留原始链接

                result = {
                    "name": name,
                    "episode_title": episode_title,
                    "url": episode_url,
                    "platform": platform,
                }
                logger.info(f"播客推荐: {name} · {episode_title}")
                return result
        except requests.exceptions.Timeout:
            logger.warning(f"播客 {name}: 请求超时，尝试下一个")
        except Exception as e:
            logger.warning(f"播客 {name}: 获取失败 ({e})，尝试下一个")

    logger.warning("所有播客源均不可用")
    return None
