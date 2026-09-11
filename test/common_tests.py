import json
import os
import shutil
import unittest
from datetime import datetime

from module.Hydro.entry import HydroHandler
from module.config import Configs
from module.utils import fuzzy_search_user, search_user_by_uid, rand_tips, get_cache_fresh_time

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


class TestCacheFreshTime(unittest.TestCase):
    """榜单缓存文件的新鲜度判定：修改时间需在 24 时前后 4 小时内"""

    def setUp(self):
        # 与其余用例保持一致，scratch 文件放在不入库的 data/ 下
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.temp_dir = os.path.join(data_dir, "cache-fresh-test")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.file_path = os.path.join(self.temp_dir, "board.json")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("{}")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _set_mtime(self, moment: datetime):
        os.utime(self.file_path, (moment.timestamp(), moment.timestamp()))

    def test_fresh_cache(self):
        for hour, minute in [(0, 30), (1, 59), (3, 59), (20, 1)]:
            with self.subTest(hour=hour, minute=minute):
                moment = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                self._set_mtime(moment)
                self.assertIsNotNone(get_cache_fresh_time(self.file_path))

    def test_stale_cache(self):
        for hour, minute in [(4, 1), (9, 50), (11, 31), (19, 59)]:
            with self.subTest(hour=hour, minute=minute):
                moment = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                self._set_mtime(moment)
                self.assertIsNone(get_cache_fresh_time(self.file_path))

    def test_fresh_time_is_mtime(self):
        moment = datetime.now().replace(hour=0, minute=30, second=0, microsecond=0)
        self._set_mtime(moment)
        self.assertEqual(get_cache_fresh_time(self.file_path).replace(microsecond=0), moment)

    def test_missing_file(self):
        self.assertIsNone(get_cache_fresh_time(os.path.join(self.temp_dir, "not-exist.json")))


if __name__ == '__main__':
    unittest.main()
