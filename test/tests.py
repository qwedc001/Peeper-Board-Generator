import unittest
from module.utils import *
from module.config import Config

config = Config("../config.json")
oj_url = config.get_config("url")


class TestUtil(unittest.TestCase):
    def test_qq(self):
        number = config.get_config("test")['qq']['number']
        name = config.get_config("test")['qq']['name']
        self.assertEqual(get_qq_name(number), name)

    def test_reload_rp(self):
        req_type = "rp"
        self.assertTrue(reload_stats(config, oj_url, req_type))

    def test_reload_problemStat(self):
        req_type = "problemStat"
        self.assertTrue(reload_stats(config, oj_url, req_type))


if __name__ == '__main__':
    unittest.main()
