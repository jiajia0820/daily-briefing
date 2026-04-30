import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

logger = get_logger("web_searcher")

TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
    "Cookie": "buvid3=daily-briefing",
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


def search_bilibili(keyword: str, count: int = 1) -> list[dict]:
    try:
        resp = requests.get(
            "https://api.bilibili.com/x/web-interface/wbi/search/type",
            params={"search_type": "video", "keyword": keyword, "page": 1},
            headers=BILI_HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("result", [])
        results = []
        for item in items:
            bvid = item.get("bvid", "")
            title = item.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
            if bvid and title:
                results.append({
                    "title": title,
                    "url": f"https://www.bilibili.com/video/{bvid}",
                })
                if len(results) >= count:
                    break
        return results
    except Exception as e:
        logger.warning(f"B站搜索失败 ({keyword}): {e}")
        return []
