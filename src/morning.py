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
from src.fetchers.bilibili_fetcher import fetch_bilibili_videos, fetch_popular_videos
from src.fetchers.hotlist_fetcher import fetch_hotlists, split_articles_by_keywords
from src.processors.llm_selector import select_articles
from src.publishers.feishu import build_morning_card, send_feishu_card
from src.utils.logger import get_logger
from src.utils.dedup import load_seen, save_seen, filter_unseen, mark_seen, cleanup_old

logger = get_logger("morning")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "config.local.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config" / "config.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config" / "config.example.yaml"
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


def _module_enabled(config: dict, module_name: str, default: bool = True) -> bool:
    return config.get("modules", {}).get("morning", {}).get(module_name, default)


def _unique_by_url(articles: list[dict]) -> list[dict]:
    seen_urls = set()
    unique_articles = []
    for article in articles:
        url = article.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique_articles.append(article)
    return unique_articles


def _exclude_urls(articles: list[dict], excluded_urls: set[str]) -> list[dict]:
    return [article for article in articles if article.get("url", "") not in excluded_urls]


def _is_foreign_article(
    article: dict,
    foreign_sources: list[str],
    foreign_url_domains: list[str],
) -> bool:
    source = article.get("source", "").lower()
    url = article.get("url", "").lower()
    if any(item.lower() in source for item in foreign_sources):
        return True
    if any(domain.lower() in url for domain in foreign_url_domains):
        return True
    return False


def _limit_foreign_articles(
    selected_articles: list[dict],
    candidate_articles: list[dict],
    count: int,
    max_foreign: int,
    foreign_sources: list[str],
    foreign_url_domains: list[str],
) -> list[dict]:
    if max_foreign < 0:
        return selected_articles[:count]

    candidates_by_url = {a.get("url", ""): a for a in candidate_articles}
    selected_urls = set()
    final_articles = []
    foreign_count = 0

    for selected in selected_articles:
        url = selected.get("url", "")
        if not url or url in selected_urls:
            continue
        article = candidates_by_url.get(url, selected)
        is_foreign = _is_foreign_article(article, foreign_sources, foreign_url_domains)
        if is_foreign and foreign_count >= max_foreign:
            continue
        selected_urls.add(url)
        foreign_count += 1 if is_foreign else 0
        final_articles.append({"title": selected.get("title", ""), "url": url})
        if len(final_articles) >= count:
            logger.info(f"国外来源限制: 保留 {foreign_count}/{max_foreign} 条")
            return final_articles

    for article in candidate_articles:
        url = article.get("url", "")
        if not url or url in selected_urls:
            continue
        is_foreign = _is_foreign_article(article, foreign_sources, foreign_url_domains)
        if is_foreign and foreign_count >= max_foreign:
            continue
        selected_urls.add(url)
        foreign_count += 1 if is_foreign else 0
        final_articles.append({"title": article.get("title", ""), "url": url})
        if len(final_articles) >= count:
            break

    logger.info(f"国外来源限制: 保留 {foreign_count}/{max_foreign} 条")
    return final_articles[:count]


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    logger.info("========== 早报开始 ==========")
    config = load_config()
    rss_sources = load_rss_sources()
    general_enabled = _module_enabled(config, "general_news", True)
    interests_enabled = _module_enabled(config, "interests", True)
    zhihu_hot_enabled = _module_enabled(config, "zhihu_hot", True)
    hotlists_enabled = _module_enabled(config, "hotlists", True)
    bilibili_enabled = _module_enabled(config, "bilibili", True)
    weather_enabled = _module_enabled(config, "weather", True)
    quote_enabled = _module_enabled(config, "quote", True)
    podcast_enabled = _module_enabled(config, "podcast", True)

    # 1. 抓取全行业 RSS
    logger.info("--- 步骤 1: 抓取 RSS ---")
    general_articles = []
    if general_enabled or interests_enabled:
        general_sources = rss_sources.get("general", [])
        general_articles = fetch_rss(general_sources)
    else:
        logger.info("全行业资讯和兴趣领域均已关闭，跳过 RSS")

    # 2. 抓取知乎热榜
    logger.info("--- 步骤 2: 抓取知乎热榜 ---")
    zhihu_articles = []
    if general_enabled or interests_enabled or zhihu_hot_enabled:
        zhihu_articles = fetch_zhihu_hot()
    else:
        logger.info("知乎相关模块已关闭，跳过知乎热榜")

    # 3. 抓取 TrendRadar/NewsNow 热榜
    logger.info("--- 步骤 3: 抓取全网热榜 ---")
    hotlist_config = config.get("hotlists", {})
    hotlist_articles = []
    hotlist_ai_articles = []
    hotlist_general_articles = []
    ai_keywords = []
    ai_routing_enabled = hotlist_config.get("route_ai_to_interests", True)
    if hotlists_enabled and hotlist_config.get("enabled", False):
        hotlist_articles = fetch_hotlists(
            sources=hotlist_config.get("sources", []),
            api_url=hotlist_config.get("api_url", ""),
            count_per_source=hotlist_config.get("count_per_source", 10),
            request_interval_ms=hotlist_config.get("request_interval_ms", 500),
        )
        if ai_routing_enabled:
            ai_keywords = list(hotlist_config.get("ai_keywords", []))
            for interest in config.get("interests", []):
                if interest.get("name", "").lower() == "ai":
                    ai_keywords.extend(interest.get("keywords", []))
            hotlist_ai_articles, hotlist_general_articles = split_articles_by_keywords(
                hotlist_articles, ai_keywords
            )
            logger.info(
                f"热榜分流: AI 兴趣 {len(hotlist_ai_articles)} 条，"
                f"全行业 {len(hotlist_general_articles)} 条"
            )
        else:
            hotlist_general_articles = hotlist_articles
    else:
        logger.info("全网热榜模块已关闭，跳过热榜抓取")

    if ai_routing_enabled and ai_keywords:
        routed_ai_articles, all_articles = split_articles_by_keywords(
            general_articles + zhihu_articles + hotlist_articles,
            ai_keywords,
        )
        routed_ai_articles = _unique_by_url(routed_ai_articles)
        logger.info(
            f"全行业候选分流: AI 兴趣 {len(routed_ai_articles)} 条，"
            f"全行业 {len(all_articles)} 条"
        )
    else:
        routed_ai_articles = hotlist_ai_articles
        all_articles = general_articles + zhihu_articles + hotlist_general_articles

    all_articles = _unique_by_url(all_articles)
    interest_candidate_articles = _unique_by_url(general_articles + zhihu_articles + hotlist_articles)

    # 4. 抓取兴趣领域 RSS
    logger.info("--- 步骤 4: 抓取兴趣领域 RSS ---")
    interest_sources = {}
    for key in rss_sources:
        if key not in ("general", "podcast"):
            interest_sources[key] = rss_sources[key]
    interest_articles = {}
    if interests_enabled:
        for key, sources in interest_sources.items():
            interest_articles[key] = fetch_rss(sources)
    else:
        logger.info("兴趣领域模块已关闭，跳过兴趣 RSS")

    # 5. 去重过滤
    logger.info("--- 步骤 5: 去重过滤 ---")
    seen_data = load_seen()
    zhihu_config = config.get("zhihu_hot", {})
    zhihu_hot = []
    if zhihu_hot_enabled and zhihu_config.get("enabled", True):
        zhihu_count = zhihu_config.get("count", 3)
        zhihu_hot = filter_unseen(zhihu_articles, seen_data)[:zhihu_count]
        logger.info(f"知乎热榜精选: {len(zhihu_hot)} 条")
        selected_zhihu_urls = {article.get("url", "") for article in zhihu_hot}
        all_articles = _exclude_urls(all_articles, selected_zhihu_urls)
        interest_candidate_articles = _exclude_urls(interest_candidate_articles, selected_zhihu_urls)
        routed_ai_articles = _exclude_urls(routed_ai_articles, selected_zhihu_urls)

    all_articles = filter_unseen(all_articles, seen_data)
    interest_candidate_articles = filter_unseen(interest_candidate_articles, seen_data)
    routed_ai_articles = filter_unseen(routed_ai_articles, seen_data)
    for key in interest_articles:
        interest_articles[key] = filter_unseen(interest_articles[key], seen_data)

    # 6. GPT 选稿
    logger.info("--- 步骤 6: GPT 选稿 ---")
    llm_config = config.get("llm", {})
    model = llm_config.get("model", "gpt-5.5")
    api_key = llm_config.get("api_key", "")
    base_url = llm_config.get("base_url", "")

    general_top5 = []
    if general_enabled:
        general_top5 = select_articles(
            all_articles, category="全行业", count=5, model=model, api_key=api_key, base_url=base_url
        )
    else:
        logger.info("全行业资讯模块已关闭，跳过 GPT 选稿")

    # 排除已被全行业选中的 URL
    general_selected_urls = {a["url"] for a in general_top5}

    interests = config.get("interests", [])
    interest_top5 = {}
    for interest in interests:
        if not interests_enabled:
            break
        name = interest["name"]
        keywords = interest.get("keywords", [])
        # 合并：兴趣领域专属源 + 全部文章中关键词匹配的
        pool = []
        # 从兴趣领域专属源获取
        for key, arts in interest_articles.items():
            pool.extend(arts)
        # 明确命中 AI 关键词的候选优先进入 AI 兴趣领域
        if name.lower() == "ai":
            pool.extend(routed_ai_articles)
        # 从全部候选文章中按关键词粗筛
        for a in interest_candidate_articles:
            title = a.get("title", "")
            if any(kw in title for kw in keywords):
                pool.append(a)
        # 去重 + 排除全行业已选
        seen_urls = set(general_selected_urls)
        unique_pool = []
        for a in pool:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                unique_pool.append(a)

        # 如果粗筛后候选不足，把全部文章给 GPT（排除已选的）
        if len(unique_pool) < 10:
            fallback_pool = interest_candidate_articles if name.lower() == "ai" else all_articles
            for a in fallback_pool:
                if a["url"] not in seen_urls:
                    seen_urls.add(a["url"])
                    unique_pool.append(a)

        target_count = 5
        max_foreign = interest.get("max_foreign")
        select_count = target_count
        if isinstance(max_foreign, int) and max_foreign >= 0:
            select_count = target_count + max_foreign

        selected_articles = select_articles(
            unique_pool, category=name, keywords=keywords, count=select_count,
            model=model, api_key=api_key, base_url=base_url
        )
        if isinstance(max_foreign, int) and max_foreign >= 0:
            selected_articles = _limit_foreign_articles(
                selected_articles=selected_articles,
                candidate_articles=unique_pool,
                count=target_count,
                max_foreign=max_foreign,
                foreign_sources=interest.get("foreign_sources", []),
                foreign_url_domains=interest.get("foreign_url_domains", []),
            )
        else:
            selected_articles = selected_articles[:target_count]

        interest_top5[name] = selected_articles

    # 5b. B站热门视频
    bilibili_videos = []
    bili_config = config.get("bilibili", {})
    if bilibili_enabled and bili_config and bili_config.get("enabled", True):
        logger.info("--- 步骤 6b: B站热门视频 ---")
        bili_count = bili_config.get("count", 5)
        bili_mode = bili_config.get("mode", "popular")
        if bili_mode == "popular":
            bili_pool = fetch_popular_videos(count=bili_count * 4)
        else:
            bili_keywords = bili_config.get("search_keywords", [])
            bili_pool = fetch_bilibili_videos(bili_keywords, count=bili_count * 3)
        bili_pool = filter_unseen(bili_pool, seen_data)
        bilibili_videos = bili_pool[:bili_count]
    else:
        logger.info("--- 步骤 6b: B站热门视频已关闭 ---")

    # 7. 记录已推送文章
    logger.info("--- 步骤 7: 记录已推送 ---")
    all_selected = list(general_top5) + list(zhihu_hot)
    for news_list in interest_top5.values():
        all_selected.extend(news_list)
    all_selected.extend(bilibili_videos)
    mark_seen(all_selected, seen_data)
    seen_data = cleanup_old(seen_data, config.get("dedup", {}).get("retention_days", 7))
    save_seen(seen_data)

    # 8. 天气
    logger.info("--- 步骤 8: 获取天气 ---")
    city = config.get("user", {}).get("city", "鼓楼")
    weather_cfg = config.get("weather", {})
    weather = None
    if weather_enabled:
        weather = fetch_weather(
            city,
            api_key=weather_cfg.get("api_key", ""),
            api_host=weather_cfg.get("api_host", ""),
        )
    else:
        logger.info("天气模块已关闭")

    # 9. 每日一句
    logger.info("--- 步骤 9: 每日一句 ---")
    quote = fetch_quote() if quote_enabled else None
    if not quote_enabled:
        logger.info("每日一句模块已关闭")

    # 10. 播客推荐
    logger.info("--- 步骤 10: 播客推荐 ---")
    podcast = None
    if podcast_enabled:
        podcast_sources = rss_sources.get("podcast", [])
        podcast = fetch_podcast(podcast_sources)
    else:
        logger.info("播客模块已关闭")

    # 11. 组装飞书卡片
    logger.info("--- 步骤 11: 组装飞书卡片 ---")
    date_str = datetime.now().strftime("%Y年%m月%d日")
    card = build_morning_card(
        general_news=general_top5,
        interest_news=interest_top5,
        zhihu_hot=zhihu_hot,
        bilibili_videos=bilibili_videos,
        bili_section_name=bili_config.get("name", "求职就业") if bili_config else "",
        weather=weather,
        quote=quote,
        podcast=podcast,
        date_str=date_str,
    )

    # 12. 推送
    logger.info("--- 步骤 12: 飞书推送 ---")
    feishu_config = config.get("publisher", {}).get("feishu", {})
    send_feishu_card(card, feishu_config)

    logger.info("========== 早报完成 ==========")


if __name__ == "__main__":
    main()
