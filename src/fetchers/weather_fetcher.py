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

        # 3. 获取当日预报（温度范围 + 白天风力）
        forecast_url = f"https://{host}/v7/weather/3d"
        forecast_resp = requests.get(
            forecast_url,
            params={"location": location_id},
            headers=headers,
            timeout=TIMEOUT,
        )
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()
        today = forecast_data.get("daily", [{}])[0]

        result = {
            "city": city_name,
            "temp": now.get("temp", "--"),
            "temp_min": today.get("tempMin", "--"),
            "temp_max": today.get("tempMax", "--"),
            "condition": now.get("text", ""),
            "condition_day": today.get("textDay", ""),
            "condition_night": today.get("textNight", ""),
            "humidity": now.get("humidity", ""),
            "wind_dir": today.get("windDirDay", now.get("windDir", "")),
            "wind_scale": today.get("windScaleDay", now.get("windScale", "")),
        }
        logger.info(
            f"天气获取成功: {city_name} {result['condition_day']} "
            f"{result['temp_min']}~{result['temp_max']}°C "
            f"{result['wind_dir']}{result['wind_scale']}级"
        )
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
        "temp_min": "--",
        "temp_max": "--",
        "condition": "暂不可用",
        "condition_day": "",
        "condition_night": "",
        "humidity": "",
        "wind_dir": "",
        "wind_scale": "",
    }
