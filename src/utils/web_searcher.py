import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

logger = get_logger("web_searcher")

TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def search_zhihu(keyword: str, count: int = 1) -> list[dict]:
    try:
        resp = requests.get(
            "https://cn.bing.com/search",
            params={"q": f"site:zhihu.com {keyword}"},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select("h2 a"):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if href and title and "zhihu.com" in href:
                results.append({"title": title, "url": href})
                if len(results) >= count:
                    break
        return results
    except Exception as e:
        logger.warning(f"知乎搜索失败 ({keyword}): {e}")
        return []


def search_xiaohongshu(keyword: str, count: int = 1) -> list[dict]:
    from urllib.parse import quote
    url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
    return [{"title": f"搜索「{keyword}」", "url": url}]
