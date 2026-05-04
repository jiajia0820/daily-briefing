import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.processors.llm_generator import generate_tip, summarize_github_repos
from src.fetchers.github_fetcher import fetch_trending_repos
from src.publishers.feishu import build_afternoon_card, send_feishu_card
from src.utils.logger import get_logger

logger = get_logger("afternoon")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "config.local.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config" / "config.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config" / "config.example.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    _resolve_env(config)
    return config


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
    return config.get("modules", {}).get("afternoon", {}).get(module_name, default)


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    logger.info("========== 午报开始 ==========")
    config = load_config()

    llm_config = config.get("llm", {})
    model = llm_config.get("model", "gpt-5.5")
    api_key = llm_config.get("api_key", "")
    base_url = llm_config.get("base_url", "")

    # 1. 生成知识卡片
    tips = []
    tip_modules = [
        ("ai_tip", "AI 技巧", "🤖", "生成 AI 技巧"),
        ("psychology", "心理学/经济学", "🧠", "生成心理学/经济学技巧"),
        ("brand_insight", "品牌洞察", "💡", "生成品牌洞察"),
    ]
    for topic_type, section_name, section_icon, log_text in tip_modules:
        if not _module_enabled(config, topic_type, True):
            logger.info(f"--- {section_name} 模块已关闭 ---")
            continue
        logger.info(f"--- {log_text} ---")
        tip = generate_tip(topic_type, model=model, api_key=api_key, base_url=base_url)
        tip["section_name"] = section_name
        tip["section_icon"] = section_icon
        tips.append(tip)

    # 2. GitHub 热门项目
    logger.info("--- 步骤 4: GitHub 热门项目 ---")
    repos = []
    if _module_enabled(config, "github_trending", True):
        repos = fetch_trending_repos(count=5)
    else:
        logger.info("GitHub Trending 模块已关闭")
    if repos:
        repos = summarize_github_repos(repos, model=model, api_key=api_key, base_url=base_url)

    # 3. 组装飞书卡片
    logger.info("--- 步骤 5: 组装飞书卡片 ---")
    date_str = datetime.now().strftime("%Y年%m月%d日")
    card = build_afternoon_card(tips=tips, date_str=date_str, github_repos=repos)

    # 4. 推送
    logger.info("--- 步骤 6: 飞书推送 ---")
    feishu_config = config.get("publisher", {}).get("feishu", {})
    send_feishu_card(card, feishu_config)

    logger.info("========== 午报完成 ==========")


if __name__ == "__main__":
    main()
