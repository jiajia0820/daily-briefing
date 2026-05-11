import os
import unittest
from unittest.mock import Mock, patch

from src.fetchers.weather_fetcher import fetch_weather


class WeatherFetcherTest(unittest.TestCase):
    def test_uses_environment_host_when_config_host_is_placeholder(self):
        responses = [
            Mock(status_code=200),
            Mock(status_code=200),
            Mock(status_code=200),
        ]
        responses[0].json.return_value = {"location": [{"id": "101190101", "name": "南京"}]}
        responses[1].json.return_value = {"now": {"temp": "20", "text": "晴", "humidity": "50", "windDir": "东风", "windScale": "3"}}
        responses[2].json.return_value = {"daily": [{"tempMin": "16", "tempMax": "24", "textDay": "晴", "textNight": "多云", "windDirDay": "东风", "windScaleDay": "3"}]}
        for response in responses:
            response.raise_for_status.return_value = None

        with patch.dict(os.environ, {"QWEATHER_API_HOST": "devapi.qweather.com"}, clear=False):
            with patch("src.fetchers.weather_fetcher.requests.get", side_effect=responses) as get:
                weather = fetch_weather(
                    "鼓楼区",
                    api_key="key",
                    api_host="your-qweather-host.example.com",
                    location="南京",
                )

        called_urls = [call.args[0] for call in get.call_args_list]
        self.assertEqual(
            called_urls,
            [
                "https://devapi.qweather.com/geo/v2/city/lookup",
                "https://devapi.qweather.com/v7/weather/now",
                "https://devapi.qweather.com/v7/weather/3d",
            ],
        )
        self.assertEqual(get.call_args_list[0].kwargs["params"]["location"], "南京")
        self.assertEqual(weather["city"], "南京")
        self.assertEqual(weather["condition_day"], "晴")


    def test_environment_host_overrides_configured_default_host(self):
        responses = [
            Mock(status_code=200),
            Mock(status_code=200),
            Mock(status_code=200),
        ]
        responses[0].json.return_value = {"location": [{"id": "101190101", "name": "南京"}]}
        responses[1].json.return_value = {"now": {"temp": "20", "text": "晴", "humidity": "50", "windDir": "东风", "windScale": "3"}}
        responses[2].json.return_value = {"daily": [{"tempMin": "16", "tempMax": "24", "textDay": "晴", "textNight": "多云", "windDirDay": "东风", "windScaleDay": "3"}]}
        for response in responses:
            response.raise_for_status.return_value = None

        with patch.dict(os.environ, {"QWEATHER_API_HOST": "api.example-qweather.test"}, clear=False):
            with patch("src.fetchers.weather_fetcher.requests.get", side_effect=responses) as get:
                fetch_weather(
                    "鼓楼区",
                    api_key="key",
                    api_host="devapi.qweather.com",
                    location="南京",
                )

        called_urls = [call.args[0] for call in get.call_args_list]
        self.assertEqual(
            called_urls,
            [
                "https://api.example-qweather.test/geo/v2/city/lookup",
                "https://api.example-qweather.test/v7/weather/now",
                "https://api.example-qweather.test/v7/weather/3d",
            ],
        )
        self.assertEqual(get.call_args_list[0].kwargs["params"]["location"], "南京")



if __name__ == "__main__":
    unittest.main()
