import requests
from src.utils.logger import get_logger

logger = get_logger("zhihu_fetcher")

ZHIHU_HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
TIMEOUT = 10


def fetch_zhihu_hot(limit: int = 30) -> list[dict]:
    try:
        logger.info("知乎热榜: 正在抓取")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.zhihu.com/hot",
        }
        resp = requests.get(ZHIHU_HOT_API, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        articles = []
        for item in items[:limit]:
            target = item.get("target", {})
            title = target.get("title", "").strip()
            question_id = target.get("id", "")
            url = f"https://www.zhihu.com/question/{question_id}" if question_id else ""
            if title and url:
                articles.append({
                    "title": title,
                    "url": url,
                    "source": "知乎热榜",
                    "category": "热榜",
                    "published_at": "",
                })
        logger.info(f"知乎热榜: 获取 {len(articles)} 条")
        return articles
    except requests.exceptions.Timeout:
        logger.warning("知乎热榜: 请求超时，已跳过")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"知乎热榜: 请求失败 ({e})，已跳过")
        return []
    except Exception as e:
        logger.warning(f"知乎热榜: 解析失败 ({e})，已跳过")
        return []
