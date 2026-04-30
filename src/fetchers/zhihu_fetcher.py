import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

logger = get_logger("zhihu_fetcher")

TOPHUB_ZHIHU = "https://tophub.today/n/mproPpoq6O"
TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_zhihu_hot(limit: int = 30) -> list[dict]:
    try:
        logger.info("知乎热榜: 正在抓取")
        resp = requests.get(TOPHUB_ZHIHU, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("table tr td.al a")
        articles = []
        for a in links[:limit]:
            title = a.get_text(strip=True)
            url = a.get("href", "")
            if title and url and "zhihu.com" in url:
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
