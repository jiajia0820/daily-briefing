import json
import os
from pathlib import Path
from src.utils.llm_client import chat_completion
from src.utils.logger import get_logger
from src.utils.web_searcher import search_zhihu, search_bilibili

logger = get_logger("llm_generator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_PATH = PROJECT_ROOT / "data" / "generated_topics.json"

TOPIC_CONFIGS = {
    "ai_tip": {
        "name": "AI 技巧",
        "prompt": """生成一条简洁实用的 AI 使用技巧，100-150 字。
要求：
- 有具体方法，读者可以立即使用
- 避免泛泛而谈，要有实操性
- 用中文回答

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "技巧正文", "topic": "主题关键词"}}""",
    },
    "psychology": {
        "name": "心理学/经济学技巧",
        "prompt": """生成一条实用的心理学或经济学知识卡片，100-150 字。
要求：
- 包含一个具体的心理学效应或经济学原理
- 解释它在日常生活或工作中的应用
- 用中文回答

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "知识卡片正文", "topic": "主题关键词"}}""",
    },
    "brand_insight": {
        "name": "品牌洞察",
        "prompt": """生成一条品牌或商业洞察，100-150 字。
要求：
- 分析一个知名品牌的策略、增长方法或创新点
- 提炼出可复用的方法论
- 用中文回答

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "洞察正文", "topic": "主题关键词"}}""",
    },
}


def generate_tip(
    topic_type: str,
    model: str = "gpt-5.5",
    api_key: str = None,
    base_url: str = None,
) -> dict:
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    config = TOPIC_CONFIGS.get(topic_type)
    if not config:
        logger.warning(f"未知的主题类型: {topic_type}")
        return {"content": "", "link": "", "topic": ""}

    if not key:
        logger.warning("OPENAI_API_KEY 未设置，无法生成内容")
        return {"content": f"今日{config['name']}暂不可用", "link": "", "topic": ""}

    history = _load_history(topic_type)
    history_str = ", ".join(history[-30:]) if history else "无"
    prompt = config["prompt"].format(history=history_str)

    try:
        content = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            api_key=key,
            base_url=base_url,
            temperature=0.7,
            max_tokens=500,
        )
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(content)
        topic_kw = result.get("topic", "")
        logger.info(f"午报内容生成成功 ({topic_type}): {topic_kw}")
        _save_history(topic_type, topic_kw)

        # 搜索真实的知乎和小红书帖子作为延伸阅读
        links = []
        if topic_kw:
            zhihu = search_zhihu(topic_kw, count=1)
            if zhihu:
                links.append({"platform": "知乎", **zhihu[0]})
            bili = search_bilibili(topic_kw, count=1)
            if bili:
                links.append({"platform": "B站", **bili[0]})
        result["links"] = links
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"GPT 返回 JSON 解析失败 ({e})")
        return {"content": f"今日{config['name']}生成失败", "link": "", "topic": ""}
    except Exception as e:
        logger.warning(f"GPT 调用失败 ({e})")
        return {"content": f"今日{config['name']}生成失败", "link": "", "topic": ""}


def summarize_github_repos(
    repos: list[dict],
    model: str = "gpt-5.5",
    api_key: str = None,
    base_url: str = None,
) -> list[dict]:
    if not repos:
        return []

    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        logger.warning("OPENAI_API_KEY 未设置，无法生成 GitHub 摘要")
        return repos

    repo_list = "\n".join(
        f"{i+1}. {r['name']} ({r.get('language','')}) — {r.get('description','无描述')} | 今日 {r.get('stars_today','?')}"
        for i, r in enumerate(repos)
    )

    prompt = f"""你是一位有品味的技术博主，擅长用简洁有趣的语言介绍开源项目。请为以下 GitHub 热门项目各写一段中文摘要（40-80字）。

要求：
- 先用一句话说清楚项目是什么、解决什么问题
- 再加一句点评：为什么值得关注（技术亮点 / 应用场景 / 行业趋势）
- 语气自然，像在跟朋友推荐，不要太官方
- 总字数控制在 40-80 字之间

项目列表：
{repo_list}

请严格返回 JSON 数组，格式如下，不要返回任何其他内容：
[{{"index": 1, "summary": "摘要正文"}}]

返回 {len(repos)} 条，不多不少。"""

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
        summaries = json.loads(content)
        if isinstance(summaries, list):
            for item in summaries:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(repos):
                    repos[idx]["summary"] = item.get("summary", "")
            logger.info(f"GitHub 项目摘要生成成功: {len(summaries)} 条")
        return repos
    except Exception as e:
        logger.warning(f"GitHub 摘要生成失败 ({e})，使用原始描述")
        for r in repos:
            r.setdefault("summary", r.get("description", ""))
        return repos


def _load_history(topic_type: str) -> list[str]:
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(topic_type, [])
    except Exception:
        pass
    return []


def _save_history(topic_type: str, topic: str):
    if not topic:
        return
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        topics = data.get(topic_type, [])
        topics.append(topic)
        topics = topics[-30:]  # 只保留最近 30 条
        data[topic_type] = topics
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存主题历史失败: {e}")
