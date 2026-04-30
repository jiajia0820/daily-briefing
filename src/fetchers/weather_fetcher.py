import os
import requests
from src.utils.logger import get_logger

logger = get_logger("weather_fetcher")

TIMEOUT = 10
# 和风天气城市查询 API
GEO_API = "https://geoapi.qweather.com/v2/city/lookup"
# 和风天气实时天气 API
WEATHER_API = "https://devapi.qweather.com/v7/weather/now"


def fetch_weather(city: str, api_key: str = None) -> dict:
    key = api_key or os.getenv("QWEATHER_API_KEY", "")
    if not key:
        logger.warning("QWEATHER_API_KEY 未设置")
        return _fallback(city)

    try:
        # 1. 查询城市 ID
        geo_resp = requests.get(
            GEO_API,
            params={"location": city, "key": key},
            timeout=TIMEOUT,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        locations = geo_data.get("location", [])
        if not locations:
            logger.warning(f"未找到城市: {city}")
            return _fallback(city)
        location_id = locations[0]["id"]

        # 2. 获取实时天气
        weather_resp = requests.get(
            WEATHER_API,
            params={"location": location_id, "key": key},
            timeout=TIMEOUT,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
        now = weather_data.get("now", {})

        result = {
            "city": city,
            "temp": now.get("temp", "--"),
            "condition": now.get("text", ""),
            "humidity": now.get("humidity", ""),
            "wind_dir": now.get("windDir", ""),
            "wind_scale": now.get("windScale", ""),
        }
        logger.info(f"天气获取成功: {city} {result['condition']} {result['temp']}°C")
        return result

    except requests.exceptions.Timeout:
        logger.warning("天气 API 请求超时")
        return _fallback(city)
    except Exception as e:
        logger.warning(f"天气获取失败: {e}")
        return _fallback(city)


def _fallback(city: str) -> dict:
    return {
        "city": city,
        "temp": "--",
        "condition": "暂不可用",
        "humidity": "",
        "wind_dir": "",
        "wind_scale": "",
    }
