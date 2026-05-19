import os
from urllib.parse import urlparse

import requests

from src.utils.logger import get_logger

logger = get_logger("weather_fetcher")

TIMEOUT = 10
DEFAULT_API_HOST = ""
PLACEHOLDER_HOSTS = {
    "your-qweather-host.example.com",
    "your-qweather-host",
}


class WeatherFetchError(Exception):
    pass


def fetch_weather(
    city: str,
    api_key: str = None,
    api_host: str = None,
    location: str = None,
) -> dict:
    key = api_key or os.getenv("QWEATHER_API_KEY", "")
    host = _resolve_host(api_host)
    if not key:
        logger.warning("QWEATHER_API_KEY is not configured")
        return _fallback(city)
    if not host:
        logger.warning("QWEATHER_API_HOST is not configured")
        return _fallback(city)

    headers = {"X-QW-Api-Key": key}

    try:
        city_name, location_id = _lookup_location(
            host=host,
            headers=headers,
            city=city,
            adm=location,
        )
        now = _request_json(
            f"https://{host}/v7/weather/now",
            params={"location": location_id},
            headers=headers,
            endpoint="weather-now",
        ).get("now", {})
        today = _request_json(
            f"https://{host}/v7/weather/3d",
            params={"location": location_id},
            headers=headers,
            endpoint="weather-3d",
        ).get("daily", [{}])[0]

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
            f"Weather fetched: {city_name} {result['condition_day']} "
            f"{result['temp_min']}~{result['temp_max']}C "
            f"{result['wind_dir']}{result['wind_scale']}"
        )
        return result
    except requests.exceptions.Timeout:
        logger.warning("Weather API request timed out")
        return _fallback(city)
    except (requests.exceptions.RequestException, WeatherFetchError) as e:
        logger.warning(f"Weather fetch failed: {e}")
        return _fallback(city)
    except Exception as e:
        logger.warning(f"Unexpected weather fetch failure: {e}")
        return _fallback(city)


def _resolve_host(api_host: str = None) -> str:
    host = _normalize_host(api_host)
    if not host or host in PLACEHOLDER_HOSTS:
        host = _normalize_host(os.getenv("QWEATHER_API_HOST", DEFAULT_API_HOST))
    if host in PLACEHOLDER_HOSTS:
        return ""
    return host


def _normalize_host(host: str = None) -> str:
    if not host:
        return ""
    host = host.strip()
    if not host:
        return ""
    if "://" in host:
        parsed = urlparse(host)
        host = parsed.netloc
    return host.strip("/")


def _lookup_location(host: str, headers: dict, city: str, adm: str = None) -> tuple[str, str]:
    params = {"location": city}
    if adm and adm != city:
        params["adm"] = adm
    data = _request_json(
        f"https://{host}/geo/v2/city/lookup",
        params=params,
        headers=headers,
        endpoint="geo-city-lookup",
    )
    locations = data.get("location", [])
    if not locations:
        place = f"{city}, {adm}" if adm else city
        raise WeatherFetchError(f"No QWeather location found for {place}")
    location = locations[0]
    return location.get("name", city), location["id"]


def _request_json(url: str, params: dict, headers: dict, endpoint: str) -> dict:
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    code = str(data.get("code", ""))
    if code and code != "200":
        raise WeatherFetchError(f"{endpoint} returned QWeather code {code}")
    return data


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
