import json
import unittest

from module.submission import fetch_submissions
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


class TestFetch(unittest.TestCase):
    def test_fetch_submissions_yesterday(self):
        result = fetch_submissions(config, True)
        with open("submission_result_yesterday.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)

    def test_fetch_submissions_today(self):
        result = fetch_submissions(config, False)
        with open("submission_result_today.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)


if __name__ == '__main__':
    unittest.main()
