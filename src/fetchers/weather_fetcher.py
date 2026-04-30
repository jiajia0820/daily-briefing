import os
import requests
from src.utils.logger import get_logger

logger = get_logger("weather_fetcher")

TIMEOUT = 10
# 和风天气专属 API Host——在 config.yaml 中配置
DEFAULT_API_HOST = "jt52qd3e2a.re.qweatherapi.com"


def fetch_weather(city: str, api_key: str = None, api_host: str = None, location: str = None) -> dict:
    key = api_key or os.getenv("QWEATHER_API_KEY", "")
    host = api_host or os.getenv("QWEATHER_API_HOST", DEFAULT_API_HOST)
    if not key:
        logger.warning("QWEATHER_API_KEY 未设置")
        return _fallback(city)

    headers = {"X-QW-Api-Key": key}

    try:
        # 1. GEO 查询城市 ID
        geo_url = f"https://{host}/geo/v2/city/lookup"
        geo_resp = requests.get(
            geo_url,
            params={"location": location or city},
            headers=headers,
            timeout=TIMEOUT,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        locations = geo_data.get("location", [])
        if not locations:
            logger.warning(f"未找到城市: {city}")
            return _fallback(city)
        location_id = locations[0]["id"]
        city_name = locations[0].get("name", city)

        # 2. 获取实时天气
        weather_url = f"https://{host}/v7/weather/now"
        weather_resp = requests.get(
            weather_url,
            params={"location": location_id},
            headers=headers,
            timeout=TIMEOUT,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
        now = weather_data.get("now", {})

        result = {
            "city": city_name,
            "temp": now.get("temp", "--"),
            "condition": now.get("text", ""),
            "humidity": now.get("humidity", ""),
            "wind_dir": now.get("windDir", ""),
            "wind_scale": now.get("windScale", ""),
        }
        logger.info(f"天气获取成功: {city_name} {result['condition']} {result['temp']}°C")
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
