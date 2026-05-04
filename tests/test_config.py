import unittest
from pathlib import Path

import yaml


class ConfigExampleTest(unittest.TestCase):
    def test_example_config_loads_required_sections(self):
        config = yaml.safe_load(Path("config/config.example.yaml").read_text(encoding="utf-8"))

        for key in [
            "user",
            "modules",
            "interests",
            "bilibili",
            "hotlists",
            "zhihu_hot",
            "publisher",
            "llm",
            "weather",
            "dedup",
        ]:
            self.assertIn(key, config)

        self.assertTrue(config["modules"]["morning"]["zhihu_hot"])
        self.assertTrue(config["modules"]["afternoon"]["github_trending"])


if __name__ == "__main__":
    unittest.main()
