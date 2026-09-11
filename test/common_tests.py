import json
import os
import unittest

from module.Hydro.entry import HydroHandler
from module.config import Configs
from module.utils import fuzzy_search_user, search_user_by_uid, rand_tips

config = Configs(os.path.join(os.path.dirname(__file__), "..", "config.json")).get_configs()[0]
oj_url = config.get_config()["url"]


class TestSearch(unittest.TestCase):
    def test_fuzzy(self):
        handler = HydroHandler(config)
        res = fuzzy_search_user(config, "qwedc001", handler)
        print(res)
        self.assertIsNotNone(res)

    def test_uid(self):
        handler = HydroHandler(config)
        res = search_user_by_uid("2", handler)
        print(res)
        self.assertIsNotNone(res)

    def test_rand_tips(self):
        res = rand_tips(config)
        print(res)
        self.assertIsNotNone(res)

# 单个 configs json 内可以包含多个 OJ 的配置，这里放一份用于测试的最小样例
MULTI_CONFIG_FIXTURE = [
    {
        "handler": "Hydro",
        "url": "http://example.com/",
        "data": "data",
        "id": "group-a",
        "board_name": "Group A Board",
    },
    {
        "handler": "Hydro",
        "url": "http://example.com/",
        "data": "data",
        "id": "group-b",
        "board_name": "Group B Board",
    },
]


class TestCLI(unittest.TestCase):
    # 对于群聊机器人的 configs 结构： configs 本身的 json 名称可以为群聊id，每个id里可以访问多个OJ
    def test_multiple_configs(self):
        filenames = ['test1.json', 'test2.json']
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        for file in filenames:
            config_path = os.path.join(data_dir, file)
            # data/ 下的文件不入库，因此在测试内生成样例，保证用例可以独立运行
            with open(config_path, "w", encoding="utf-8") as fixture:
                json.dump(MULTI_CONFIG_FIXTURE, fixture, ensure_ascii=False, indent=2)
            configs = Configs(config_path).get_configs()
            self.assertGreater(len(configs), 0, f"No configs found in {file}")
            for cfg in configs:
                self.assertIn('handler', cfg.get_config(), f"Handler not found in {file}")
                self.assertIn('url', cfg.get_config(), f"URL not found in {file}")

if __name__ == '__main__':
    unittest.main()
