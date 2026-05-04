import unittest

from src.morning import (
    _exclude_urls,
    _limit_foreign_articles,
    _module_enabled,
    _unique_by_url,
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


if __name__ == "__main__":
    unittest.main()
