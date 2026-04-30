import os
import json
import requests
from src.utils.logger import get_logger

logger = get_logger("llm_client")

TIMEOUT = 60


def chat_completion(
    messages: list[dict],
    model: str = "gpt-5.5",
    api_key: str = None,
    base_url: str = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    endpoint = f"{url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()
    return content
