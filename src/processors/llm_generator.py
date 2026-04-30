import json
import os
from pathlib import Path
from openai import OpenAI
from src.utils.logger import get_logger

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
- 附一个相关的延伸阅读链接（真实可访问的 URL）

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "技巧正文", "link": "延伸阅读URL", "topic": "主题关键词"}}""",
    },
    "psychology": {
        "name": "心理学/经济学技巧",
        "prompt": """生成一条实用的心理学或经济学知识卡片，100-150 字。
要求：
- 包含一个具体的心理学效应或经济学原理
- 解释它在日常生活或工作中的应用
- 用中文回答
- 附一个相关的延伸阅读链接（真实可访问的 URL）

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "知识卡片正文", "link": "延伸阅读URL", "topic": "主题关键词"}}""",
    },
    "brand_insight": {
        "name": "品牌洞察",
        "prompt": """生成一条品牌或商业洞察，100-150 字。
要求：
- 分析一个知名品牌的策略、增长方法或创新点
- 提炼出可复用的方法论
- 用中文回答
- 附一个相关的延伸阅读链接（真实可访问的 URL）

避免重复这些已生成过的主题：{history}

请严格返回 JSON 格式：
{{"content": "洞察正文", "link": "延伸阅读URL", "topic": "主题关键词"}}""",
    },
}


def generate_tip(
    topic_type: str,
    model: str = "gpt-4o-mini",
    api_key: str = None,
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
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(content)
        logger.info(f"午报内容生成成功 ({topic_type}): {result.get('topic', '')}")
        _save_history(topic_type, result.get("topic", ""))
        return result
    except json.JSONDecodeError as e:
        logger.warning(f"GPT 返回 JSON 解析失败 ({e})")
        return {"content": f"今日{config['name']}生成失败", "link": "", "topic": ""}
    except Exception as e:
        logger.warning(f"GPT 调用失败 ({e})")
        return {"content": f"今日{config['name']}生成失败", "link": "", "topic": ""}


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
