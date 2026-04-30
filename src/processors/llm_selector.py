import json
import os
from src.utils.llm_client import chat_completion
from src.utils.logger import get_logger

logger = get_logger("llm_selector")


def select_articles(
    articles: list[dict],
    category: str,
    keywords: list[str] = None,
    count: int = 5,
    model: str = "gpt-5.5",
    api_key: str = None,
    base_url: str = None,
) -> list[dict]:
    if not articles:
        logger.warning("没有文章可供选择")
        return []

    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        logger.warning("OPENAI_API_KEY 未设置，使用降级策略（按时间倒序）")
        return _fallback_select(articles, count)

    article_list = "\n".join(
        f"{i+1}. [{a['title']}]({a['url']}) — {a['source']}"
        for i, a in enumerate(articles)
    )

    if keywords:
        keyword_hint = f"\n关注领域关键词：{', '.join(keywords)}"
    else:
        keyword_hint = ""

    prompt = f"""你是一位资深新闻编辑。从以下文章列表中选出最有价值的 {count} 篇。

选择标准：
- 影响力：对行业或社会有重大影响
- 时效性：最新最热的动态优先
- 信息增量：能带来新知识或新视角{keyword_hint}

文章列表：
{article_list}

请严格返回 JSON 数组，格式如下，不要返回任何其他内容：
[{{"title": "文章标题", "url": "文章链接"}}]

只返回 {count} 篇，不多不少。"""

    try:
        content = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            api_key=key,
            base_url=base_url,
            temperature=0.3,
            max_tokens=1000,
        )
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        selected = json.loads(content)
        if isinstance(selected, list) and len(selected) > 0:
            logger.info(f"GPT 选稿完成（{category}）：{len(selected)} 篇")
            return selected[:count]
        else:
            logger.warning(f"GPT 返回格式异常，使用降级策略")
            return _fallback_select(articles, count)
    except json.JSONDecodeError as e:
        logger.warning(f"GPT 返回 JSON 解析失败 ({e})，使用降级策略")
        return _fallback_select(articles, count)
    except Exception as e:
        logger.warning(f"GPT 调用失败 ({e})，使用降级策略")
        return _fallback_select(articles, count)


def _fallback_select(articles: list[dict], count: int) -> list[dict]:
    logger.info(f"降级策略：取前 {count} 篇")
    return [{"title": a["title"], "url": a["url"]} for a in articles[:count]]
