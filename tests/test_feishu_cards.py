import unittest

from src.publishers.feishu import build_afternoon_card, build_morning_card


class FeishuCardTest(unittest.TestCase):
    def test_morning_card_includes_zhihu_section_and_skips_empty_general(self):
        card = build_morning_card(
            general_news=[],
            zhihu_hot=[
                {"title": "知乎 1", "url": "https://zhihu.com/question/1"},
                {"title": "知乎 2", "url": "https://zhihu.com/question/2"},
            ],
            interest_news={"AI": [{"title": "AI 1", "url": "https://example.com/ai"}]},
            date_str="2026年05月04日",
        )
        markdown = "\n".join(
            element["content"]
            for element in card["elements"]
            if element.get("tag") == "markdown"
        )

        self.assertNotIn("全行业资讯", markdown)
        self.assertIn("知乎热榜", markdown)
        self.assertIn("AI · 兴趣领域", markdown)

    def test_afternoon_card_uses_explicit_section_names(self):
        card = build_afternoon_card(
            tips=[
                {
                    "section_name": "品牌洞察",
                    "section_icon": "💡",
                    "content": "测试内容",
                    "links": [],
                }
            ],
            date_str="2026年05月04日",
            github_repos=[],
        )
        markdown = "\n".join(
            element["content"]
            for element in card["elements"]
            if element.get("tag") == "markdown"
        )

        self.assertIn("品牌洞察", markdown)
        self.assertNotIn("AI 技巧", markdown)


if __name__ == "__main__":
    unittest.main()
