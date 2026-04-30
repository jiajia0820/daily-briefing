import requests
from src.utils.logger import get_logger

logger = get_logger("bilibili_fetcher")

TIMEOUT = 10

# B站 WBI 搜索 API
SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://search.bilibili.com",
    "Cookie": "buvid3=daily-briefing",
}


def fetch_bilibili_videos(keywords: list[str], count: int = 10) -> list[dict]:
    all_videos = []
    seen_bvids = set()

    for kw in keywords:
        try:
            logger.info(f"B站搜索: {kw}")
            resp = requests.get(
                SEARCH_API,
                params={
                    "search_type": "video",
                    "keyword": kw,
                    "order": "pubdate",
                    "page": 1,
                },
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            for item in results:
                bvid = item.get("bvid", "")
                if bvid and bvid not in seen_bvids:
                    seen_bvids.add(bvid)
                    # 清理标题中的高亮标签
                    title = item.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
                    video = {
                        "title": title,
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "source": "B站",
                        "author": item.get("author", ""),
                        "category": "求职就业",
                    }
                    all_videos.append(video)
            logger.info(f"B站搜索 '{kw}': 获取 {len(results)} 条视频")
        except Exception as e:
            logger.warning(f"B站搜索 '{kw}' 失败: {e}")

    logger.info(f"B站视频抓取完成，共 {len(all_videos)} 条")
    return all_videos[:count * 3]  # 返回多一些给 GPT 筛选
