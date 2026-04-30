import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

logger = get_logger("web_searcher")

TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def search_related(keyword: str, site: str = "", count: int = 1) -> list[dict]:
    query = f"site:{site} {keyword}" if site else keyword
    try:
        resp = requests.get(
            "https://cn.bing.com/search",
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("h2 a")
        results = []
        for a in links:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if href and title and href.startswith("http"):
                results.append({"title": title, "url": href})
                if len(results) >= count:
                    break
        return results
    except Exception as e:
        logger.warning(f"搜索失败 ({site or 'web'}, {keyword}): {e}")
        return []


def search_zhihu(keyword: str, count: int = 1) -> list[dict]:
    return search_related(keyword, site="zhihu.com", count=count)


def search_xiaohongshu(keyword: str, count: int = 1) -> list[dict]:
    return search_related(keyword, site="xiaohongshu.com", count=count)
