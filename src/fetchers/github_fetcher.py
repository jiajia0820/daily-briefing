import requests
from bs4 import BeautifulSoup
from src.utils.logger import get_logger

logger = get_logger("github_fetcher")

TRENDING_URL = "https://github.com/trending"
TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch_trending_repos(count: int = 5) -> list[dict]:
    try:
        logger.info("GitHub Trending: 正在抓取")
        resp = requests.get(TRENDING_URL, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article.Box-row")
        repos = []
        for art in articles[:count]:
            h2 = art.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip().lstrip("/")
            desc_p = art.select_one("p")
            desc = desc_p.get_text(strip=True) if desc_p else ""
            lang_span = art.select_one("span[itemprop='programmingLanguage']")
            lang = lang_span.get_text(strip=True) if lang_span else ""
            stars_span = art.select("span.d-inline-block.float-sm-right")
            stars_today = stars_span[0].get_text(strip=True) if stars_span else ""
            repos.append({
                "name": repo_path,
                "url": f"https://github.com/{repo_path}",
                "description": desc,
                "language": lang,
                "stars_today": stars_today,
            })
        logger.info(f"GitHub Trending: 获取 {len(repos)} 个项目")
        return repos
    except Exception as e:
        logger.warning(f"GitHub Trending 抓取失败: {e}")
        return []
