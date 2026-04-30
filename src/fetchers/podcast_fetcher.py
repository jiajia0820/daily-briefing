import json
import requests
from src.utils.logger import get_logger

logger = get_logger("podcast_fetcher")

TIMEOUT = 10
XYZ_BASE = "https://www.xiaoyuzhoufm.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _fetch_xiaoyuzhoufm(pid: str) -> dict | None:
    url = f"{XYZ_BASE}/podcast/{pid}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    text = resp.text
    marker = '__NEXT_DATA__" type="application/json">'
    s = text.find(marker)
    if s < 0:
        return None
    s += len(marker)
    e = text.find("</script>", s)
    data = json.loads(text[s:e])
    podcast = data["props"]["pageProps"]["podcast"]
    episodes = podcast.get("episodes", [])
    if not episodes:
        return None
    ep = episodes[0]
    eid = ep.get("eid", "")
    return {
        "name": podcast.get("title", ""),
        "episode_title": ep.get("title", "").strip(),
        "url": f"{XYZ_BASE}/episode/{eid}",
        "platform": "xiaoyuzhoufm",
    }


def fetch_podcast(sources: list[dict]) -> dict | None:
    for source in sources:
        name = source.get("name", "unknown")
        platform = source.get("platform", "")
        pid = source.get("pid", "")
        try:
            if platform == "xiaoyuzhoufm" and pid:
                logger.info(f"播客 {name}: 正在从小宇宙抓取")
                result = _fetch_xiaoyuzhoufm(pid)
                if result:
                    logger.info(f"播客推荐: {result['name']} · {result['episode_title']}")
                    return result
                else:
                    logger.warning(f"播客 {name}: 未获取到单集，尝试下一个")
            else:
                logger.warning(f"播客 {name}: 不支持的平台 ({platform})，跳过")
        except requests.exceptions.Timeout:
            logger.warning(f"播客 {name}: 请求超时，尝试下一个")
        except Exception as e:
            logger.warning(f"播客 {name}: 获取失败 ({e})，尝试下一个")

    logger.warning("所有播客源均不可用")
    return None
