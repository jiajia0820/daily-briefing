import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.fetchers.rss_fetcher import fetch_rss
from src.fetchers.zhihu_fetcher import fetch_zhihu_hot
from src.fetchers.weather_fetcher import fetch_weather
from src.fetchers.quote_fetcher import fetch_quote
from src.fetchers.podcast_fetcher import fetch_podcast
from src.processors.llm_selector import select_articles
from src.publishers.feishu import build_morning_card, send_feishu_card
from src.utils.logger import get_logger
from src.utils.dedup import load_seen, save_seen, filter_unseen, mark_seen, cleanup_old

logger = get_logger("morning")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # 替换环境变量占位符
    _resolve_env(config)
    return config


def load_rss_sources() -> dict:
    sources_path = PROJECT_ROOT / "config" / "rss_sources.yaml"
    with open(sources_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_env(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_var = v[2:-1]
                obj[k] = os.getenv(env_var, "")
            else:
                _resolve_env(v)
    elif isinstance(obj, list):
        for item in obj:
            _resolve_env(item)


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    logger.info("========== 早报开始 ==========")
    config = load_config()
    rss_sources = load_rss_sources()

    # 1. 抓取全行业 RSS
    logger.info("--- 步骤 1: 抓取 RSS ---")
    general_sources = rss_sources.get("general", [])
    general_articles = fetch_rss(general_sources)

    # 2. 抓取知乎热榜
    logger.info("--- 步骤 2: 抓取知乎热榜 ---")
    zhihu_articles = fetch_zhihu_hot()
    all_articles = general_articles + zhihu_articles

    # 3. 抓取兴趣领域 RSS
    logger.info("--- 步骤 3: 抓取兴趣领域 RSS ---")
    interest_sources = {}
    for key in rss_sources:
        if key not in ("general", "podcast"):
            interest_sources[key] = rss_sources[key]
    interest_articles = {}
    for key, sources in interest_sources.items():
        interest_articles[key] = fetch_rss(sources)

    # 4. 去重过滤
    logger.info("--- 步骤 4: 去重过滤 ---")
    seen_data = load_seen()
    all_articles = filter_unseen(all_articles, seen_data)
    for key in interest_articles:
        interest_articles[key] = filter_unseen(interest_articles[key], seen_data)

    # 5. GPT 选稿
    logger.info("--- 步骤 5: GPT 选稿 ---")
    llm_config = config.get("llm", {})
    model = llm_config.get("model", "gpt-4o-mini")
    api_key = llm_config.get("api_key", "")

    general_top5 = select_articles(
        all_articles, category="全行业", count=5, model=model, api_key=api_key
    )

    interests = config.get("interests", [])
    interest_top5 = {}
    for interest in interests:
        name = interest["name"]
        keywords = interest.get("keywords", [])
        # 合并：兴趣领域专属源 + 全部文章中关键词匹配的
        pool = []
        # 从兴趣领域专属源获取
        for key, arts in interest_articles.items():
            pool.extend(arts)
        # 从全部文章中按关键词粗筛
        for a in all_articles:
            title = a.get("title", "")
            if any(kw in title for kw in keywords):
                pool.append(a)
        # 去重
        seen_urls = set()
        unique_pool = []
        for a in pool:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                unique_pool.append(a)

        interest_top5[name] = select_articles(
            unique_pool, category=name, keywords=keywords, count=5,
            model=model, api_key=api_key
        )

    # 6. 记录已推送文章
    logger.info("--- 步骤 6: 记录已推送 ---")
    all_selected = list(general_top5)
    for news_list in interest_top5.values():
        all_selected.extend(news_list)
    mark_seen(all_selected, seen_data)
    seen_data = cleanup_old(seen_data, config.get("dedup", {}).get("retention_days", 7))
    save_seen(seen_data)

    # 7. 天气
    logger.info("--- 步骤 7: 获取天气 ---")
    city = config.get("user", {}).get("city", "北京")
    weather_key = config.get("weather", {}).get("api_key", "")
    weather = fetch_weather(city, api_key=weather_key)

    # 8. 每日一句
    logger.info("--- 步骤 8: 每日一句 ---")
    quote = fetch_quote()

    # 9. 播客推荐
    logger.info("--- 步骤 9: 播客推荐 ---")
    podcast_sources = rss_sources.get("podcast", [])
    podcast = fetch_podcast(podcast_sources)

    # 10. 组装飞书卡片
    logger.info("--- 步骤 10: 组装飞书卡片 ---")
    date_str = datetime.now().strftime("%Y年%m月%d日")
    card = build_morning_card(
        general_news=general_top5,
        interest_news=interest_top5,
        weather=weather,
        quote=quote,
        podcast=podcast,
        date_str=date_str,
    )

    # 11. 推送
    logger.info("--- 步骤 11: 飞书推送 ---")
    webhook_url = config.get("publisher", {}).get("feishu", {}).get("webhook_url", "")
    if not webhook_url:
        logger.error("飞书 Webhook URL 未配置，跳过推送")
    else:
        send_feishu_card(webhook_url, card)

    logger.info("========== 早报完成 ==========")


if __name__ == "__main__":
    main()
