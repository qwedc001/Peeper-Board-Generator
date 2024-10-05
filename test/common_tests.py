import os
import unittest

from module.Hydro.entry import HydroHandler
from module.config import Configs
from module.utils import fuzzy_search_user, search_user_by_uid, rand_tips

config = Configs(os.path.join(os.path.dirname(__file__), "..")).get_configs()[0]
oj_url = config.get_config()["url"]


class TestSearch(unittest.TestCase):
    def test_fuzzy(self):
        handler = HydroHandler(config)
        res = fuzzy_search_user(config, "qwedc001", handler)
        print(res)
        self.assertIsNotNone(res)

    def test_uid(self):
        handler = HydroHandler(config)
        res = search_user_by_uid(config, "2", handler)
        print(res)
        self.assertIsNotNone(res)

    def test_rand_tips(self):
        res = rand_tips(config)
        print(res)
        self.assertIsNotNone(res)

if __name__ == '__main__':
    unittest.main()
