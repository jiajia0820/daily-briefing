import json
import time
import requests
from src.utils.logger import get_logger

logger = get_logger("feishu")

MAX_RETRIES = 2
RETRY_DELAY = 5


def send_feishu_card(webhook_url: str, card: dict) -> bool:
    payload = {
        "msg_type": "interactive",
        "card": card,
    }
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                logger.info("飞书推送成功")
                return True
            else:
                logger.warning(f"飞书返回异常: {result}")
        except Exception as e:
            logger.warning(f"飞书推送失败 (第 {attempt+1} 次): {e}")
        if attempt < MAX_RETRIES:
            logger.info(f"等待 {RETRY_DELAY}s 后重试...")
            time.sleep(RETRY_DELAY)
    logger.error("飞书推送最终失败，已达最大重试次数")
    return False


def build_morning_card(
    general_news: list[dict],
    interest_news: dict[str, list[dict]],
    weather: dict = None,
    quote: dict = None,
    podcast: dict = None,
    date_str: str = "",
) -> dict:
    elements = []

    # 天气 + 日期 头部
    header_text = f"📅 早报 · {date_str}"
    if weather:
        city = weather.get("city", "")
        temp = weather.get("temp", "--")
        condition = weather.get("condition", "")
        header_text = f"☀️ 早报 · {date_str} · {city} {condition} {temp}°C"

    # 全行业资讯
    general_md = "**━━ 全行业资讯 ━━**\n"
    for i, a in enumerate(general_news, 1):
        general_md += f"{i}. [{a['title']}]({a['url']})\n"
    elements.append({"tag": "markdown", "content": general_md})
    elements.append({"tag": "hr"})

    # 兴趣领域
    for interest_name, news_list in interest_news.items():
        interest_md = f"**━━ {interest_name} · 兴趣领域 ━━**\n"
        for i, a in enumerate(news_list, 1):
            interest_md += f"{i}. [{a['title']}]({a['url']})\n"
        elements.append({"tag": "markdown", "content": interest_md})
        elements.append({"tag": "hr"})

    # 播客推荐
    if podcast:
        podcast_md = "**━━ 播客推荐 ━━**\n"
        podcast_md += f"🎙️ {podcast.get('name', '')} · 《{podcast.get('episode_title', '')}》\n"
        podcast_md += f"[收听链接]({podcast.get('url', '')})"
        elements.append({"tag": "markdown", "content": podcast_md})
        elements.append({"tag": "hr"})

    # 每日一句
    if quote:
        quote_md = f"**━━ 每日一句 ━━**\n"
        quote_md += f"💬 \"{quote.get('text', '')}\" —— {quote.get('author', '')}"
        elements.append({"tag": "markdown", "content": quote_md})

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": header_text},
            "template": "blue",
        },
        "elements": elements,
    }
    return card


def build_afternoon_card(
    tips: list[dict],
    date_str: str = "",
) -> dict:
    elements = []

    section_icons = ["🤖", "🧠", "💡"]
    section_names = ["AI 技巧", "心理学/经济学", "品牌洞察"]

    for i, tip in enumerate(tips):
        name = section_names[i] if i < len(section_names) else "知识卡片"
        icon = section_icons[i] if i < len(section_icons) else "📌"
        tip_md = f"**━━ {icon} {name} ━━**\n"
        tip_md += tip.get("content", "")
        link = tip.get("link", "")
        if link:
            tip_md += f"\n\n📖 [延伸阅读]({link})"
        elements.append({"tag": "markdown", "content": tip_md})
        if i < len(tips) - 1:
            elements.append({"tag": "hr"})

    card = {
        "header": {
            "title": {"tag": "plain_text", "content": f"🧠 午报 · {date_str}"},
            "template": "purple",
        },
        "elements": elements,
    }
    return card
