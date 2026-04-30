import json
import hashlib
from datetime import datetime
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("quote_fetcher")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def fetch_quote(quotes_path: str = None) -> dict:
    path = Path(quotes_path) if quotes_path else PROJECT_ROOT / "config" / "quotes.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            quotes = json.load(f)
        if not quotes:
            logger.warning("名言库为空")
            return {"text": "今天也要加油哦！", "author": "daily-briefing"}

        # 根据日期 hash 选择，保证同一天同一句
        today = datetime.now().strftime("%Y-%m-%d")
        index = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(quotes)
        quote = quotes[index]
        logger.info(f"每日一句: \"{quote['text']}\" —— {quote['author']}")
        return quote
    except Exception as e:
        logger.warning(f"名言获取失败: {e}")
        return {"text": "今天也要加油哦！", "author": "daily-briefing"}
