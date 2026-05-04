import unittest
from unittest.mock import Mock, patch

from src.fetchers.hotlist_fetcher import fetch_hotlists, split_articles_by_keywords


class HotlistFetcherTest(unittest.TestCase):
    @patch("src.fetchers.hotlist_fetcher.requests.get")
    def test_fetch_hotlists_maps_items_to_articles(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "status": "cache",
            "updatedTime": 1777875340513,
            "items": [
                {"title": "AI 新进展", "url": "https://example.com/ai"},
                {"title": "普通新闻", "mobileUrl": "https://m.example.com/news"},
            ],
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        articles = fetch_hotlists(
            [{"id": "weibo", "name": "微博"}],
            api_url="https://example.com/api/s",
            count_per_source=2,
            request_interval_ms=0,
        )

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["source"], "全网热榜 · 微博")
        self.assertEqual(articles[0]["platform_id"], "weibo")
        self.assertEqual(articles[0]["rank"], 1)
        self.assertEqual(articles[1]["url"], "https://m.example.com/news")

    def test_split_articles_by_keywords(self):
        articles = [
            {"title": "OpenAI 发布新模型"},
            {"title": "普通财经新闻"},
        ]

        matched, unmatched = split_articles_by_keywords(articles, ["openai"])

        self.assertEqual(matched, [articles[0]])
        self.assertEqual(unmatched, [articles[1]])


if __name__ == "__main__":
    unittest.main()
