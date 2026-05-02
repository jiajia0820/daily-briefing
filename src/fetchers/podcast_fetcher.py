import json
import requests
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("podcast_fetcher")

TIMEOUT = 10
XYZ_BASE = "https://www.xiaoyuzhoufm.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "podcast_history.json"


def _fetch_xiaoyuzhoufm(pid: str, max_episodes: int = 3) -> list[dict]:
    url = f"{XYZ_BASE}/podcast/{pid}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    text = resp.text
    marker = '__NEXT_DATA__" type="application/json">'
    s = text.find(marker)
    if s < 0:
        return []
    s += len(marker)
    e = text.find("</script>", s)
    data = json.loads(text[s:e])
    podcast = data["props"]["pageProps"]["podcast"]
    episodes = podcast.get("episodes", [])
    results = []
    for ep in episodes[:max_episodes]:
        eid = ep.get("eid", "")
        if eid:
            results.append({
                "name": podcast.get("title", ""),
                "episode_title": ep.get("title", "").strip(),
                "url": f"{XYZ_BASE}/episode/{eid}",
                "eid": eid,
                "platform": "xiaoyuzhoufm",
            })
    return results


def _load_history() -> list[str]:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(eid: str):
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        history = _load_history()
        history.append(eid)
        history = history[-50:]  # 保留最近 50 条
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存播客推荐历史失败: {e}")


def fetch_podcast(sources: list[dict]) -> dict | None:
    all_episodes = []
    for source in sources:
        name = source.get("name", "unknown")
        platform = source.get("platform", "")
        pid = source.get("pid", "")
        try:
            if platform == "xiaoyuzhoufm" and pid:
                logger.info(f"播客 {name}: 正在从小宇宙抓取")
                eps = _fetch_xiaoyuzhoufm(pid, max_episodes=3)
                all_episodes.extend(eps)
                logger.info(f"播客 {name}: 获取 {len(eps)} 期")
            else:
                logger.warning(f"播客 {name}: 不支持的平台 ({platform})，跳过")
        except requests.exceptions.Timeout:
            logger.warning(f"播客 {name}: 请求超时，跳过")
        except Exception as e:
            logger.warning(f"播客 {name}: 获取失败 ({e})，跳过")

    if not all_episodes:
        logger.warning("所有播客源均不可用")
        return None

    # 去重：排除已推荐过的集数
    history = set(_load_history())
    unseen = [ep for ep in all_episodes if ep.get("eid") not in history]

    # 如果全部推荐过，重置历史，从头来
    if not unseen:
        logger.info("所有集数均已推荐过，重置历史")
        unseen = all_episodes
        try:
            HISTORY_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    pick = unseen[0]
    _save_history(pick.get("eid", ""))
    logger.info(f"播客推荐: {pick['name']} · {pick['episode_title']}")
    return pick
