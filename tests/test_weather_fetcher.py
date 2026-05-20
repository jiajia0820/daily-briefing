import os
import unittest
from unittest.mock import patch

from src.fetchers.weather_fetcher import fetch_weather


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class WeatherFetcherTest(unittest.TestCase):
    def test_placeholder_host_uses_env_host_and_adm_filter(self):
        responses = [
            FakeResponse({"code": "200", "location": [{"id": "101190101", "name": "Gulou"}]}),
            FakeResponse({"code": "200", "now": {"temp": "23", "text": "Cloudy", "humidity": "80"}}),
            FakeResponse(
                {
                    "code": "200",
                    "daily": [
                        {
                            "tempMin": "20",
                            "tempMax": "27",
                            "textDay": "Rain",
                            "textNight": "Cloudy",
                            "windDirDay": "East",
                            "windScaleDay": "3",
                        }
                    ],
                }
            ),
        ]

        with patch.dict(os.environ, {"QWEATHER_API_HOST": "env.qweather.example"}):
            with patch("src.fetchers.weather_fetcher.requests.get", side_effect=responses) as get:
                result = fetch_weather(
                    "Gulou",
                    api_key="test-key",
                    api_host="your-qweather-host.example.com",
                    location="Nanjing",
                )

        self.assertEqual(result["city"], "Gulou")
        self.assertEqual(result["temp"], "23")
        self.assertEqual(result["temp_min"], "20")
        self.assertEqual(result["temp_max"], "27")
        self.assertEqual(get.call_args_list[0].args[0], "https://env.qweather.example/geo/v2/city/lookup")
        self.assertEqual(get.call_args_list[0].kwargs["params"], {"location": "Gulou", "adm": "Nanjing"})

    def test_qweather_error_code_returns_fallback(self):
        with patch("src.fetchers.weather_fetcher.requests.get", return_value=FakeResponse({"code": "401"})):
            result = fetch_weather("Gulou", api_key="test-key", api_host="host.example")

        self.assertEqual(result["city"], "Gulou")
        self.assertEqual(result["temp"], "--")

    def test_missing_host_returns_fallback_without_request(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.fetchers.weather_fetcher.requests.get") as get:
                result = fetch_weather("Gulou", api_key="test-key", api_host="")

        self.assertEqual(result["city"], "Gulou")
        self.assertEqual(result["temp"], "--")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
