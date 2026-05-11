import unittest
from unittest.mock import patch

from src.morning import (
    _exclude_urls,
    _limit_foreign_articles,
    _module_enabled,
    _unique_by_url,
    main,
)


class MorningHelpersTest(unittest.TestCase):
    def test_module_enabled_defaults_to_true(self):
        self.assertTrue(_module_enabled({}, "weather"))
        self.assertFalse(_module_enabled({"modules": {"morning": {"weather": False}}}, "weather"))

    def test_unique_by_url_keeps_first_item(self):
        articles = [
            {"title": "A", "url": "https://example.com/a"},
            {"title": "A again", "url": "https://example.com/a"},
            {"title": "B", "url": "https://example.com/b"},
        ]

        unique = _unique_by_url(articles)

        self.assertEqual([item["title"] for item in unique], ["A", "B"])

    def test_exclude_urls(self):
        articles = [
            {"title": "A", "url": "https://example.com/a"},
            {"title": "B", "url": "https://example.com/b"},
        ]

        result = _exclude_urls(articles, {"https://example.com/a"})

        self.assertEqual(result, [articles[1]])

    def test_limit_foreign_articles_refills_with_local_candidates(self):
        candidates = [
            {"title": "OpenAI A", "url": "https://openai.com/a", "source": "OpenAI Blog"},
            {"title": "HF B", "url": "https://huggingface.co/b", "source": "Hugging Face Blog"},
            {"title": "OpenAI C", "url": "https://openai.com/c", "source": "OpenAI Blog"},
            {"title": "量子位 D", "url": "https://qbitai.com/d", "source": "量子位"},
            {"title": "知乎 E", "url": "https://zhihu.com/e", "source": "知乎热榜"},
        ]
        selected = [{"title": item["title"], "url": item["url"]} for item in candidates[:4]]

        result = _limit_foreign_articles(
            selected_articles=selected,
            candidate_articles=candidates,
            count=4,
            max_foreign=2,
            foreign_sources=["Hugging Face Blog", "OpenAI Blog"],
            foreign_url_domains=["huggingface.co", "openai.com"],
        )

        foreign_count = sum(
            "openai.com" in item["url"] or "huggingface.co" in item["url"]
            for item in result
        )
        self.assertEqual(len(result), 4)
        self.assertEqual(foreign_count, 2)
        self.assertEqual(result[-1]["title"], "知乎 E")

    @patch("src.morning.send_feishu_card")
    @patch("src.morning.build_morning_card", return_value={})
    @patch("src.morning.fetch_podcast")
    @patch("src.morning.fetch_quote")
    @patch("src.morning.fetch_weather")
    @patch("src.morning.save_seen")
    @patch("src.morning.cleanup_old", return_value={})
    @patch("src.morning.mark_seen")
    @patch("src.morning.load_seen", return_value={})
    @patch("src.morning.load_rss_sources", return_value={})
    @patch("src.morning.load_config")
    def test_main_passes_city_and_adm_to_weather_fetcher(
        self,
        load_config,
        _load_rss_sources,
        _load_seen,
        _mark_seen,
        _cleanup_old,
        _save_seen,
        fetch_weather,
        _fetch_quote,
        _fetch_podcast,
        _build_morning_card,
        _send_feishu_card,
    ):
        load_config.return_value = {
            "user": {"city": "鼓楼区", "city_adm": "南京"},
            "modules": {
                "morning": {
                    "general_news": False,
                    "zhihu_hot": False,
                    "interests": False,
                    "hotlists": False,
                    "bilibili": False,
                    "weather": True,
                    "quote": False,
                    "podcast": False,
                }
            },
            "weather": {"api_key": "key", "api_host": "host"},
            "dedup": {"retention_days": 7},
        }

        main()

        fetch_weather.assert_called_once_with(
            "鼓楼区",
            api_key="key",
            api_host="host",
            location="南京",
        )


if __name__ == "__main__":
    unittest.main()
