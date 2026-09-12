import argparse
import json
import os
import shutil
import unittest
from datetime import datetime, timedelta

from main import parse_full_date
from module.Hydro.entry import HydroHandler
from module.board.misc import MiscBoardGenerator
from module.config import Config, Configs
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
    """榜单缓存文件的新鲜度判定：mtime 需在「文件名所记录日期结束（次日 0 点）」前后 4 小时内"""

    CACHE_DATE = "2026-07-25"
    MIDNIGHT = datetime(2026, 7, 26)  # 该日结束的时刻，新鲜窗口的中心

    def setUp(self):
        # 与其余用例保持一致，scratch 文件放在不入库的 data/ 下
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.temp_dir = os.path.join(data_dir, "cache-fresh-test")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.file_path = os.path.join(self.temp_dir, f"some-board-{self.CACHE_DATE}.json")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("{}")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _set_mtime(self, moment: datetime):
        os.utime(self.file_path, (moment.timestamp(), moment.timestamp()))

    def test_fresh_cache(self):
        for delta in (timedelta(hours=-3, minutes=-59), timedelta(hours=-1), timedelta(0),
                      timedelta(hours=3, minutes=59)):
            with self.subTest(delta=delta):
                self._set_mtime(self.MIDNIGHT + delta)
                self.assertIsNotNone(get_cache_fresh_time(self.file_path))

    def test_stale_cache(self):
        for delta in (timedelta(hours=-4, minutes=-1), timedelta(hours=-12),
                      timedelta(hours=4, minutes=1), timedelta(days=1)):
            with self.subTest(delta=delta):
                self._set_mtime(self.MIDNIGHT + delta)
                self.assertIsNone(get_cache_fresh_time(self.file_path))

    def test_fresh_time_is_mtime(self):
        moment = self.MIDNIGHT + timedelta(minutes=30)
        self._set_mtime(moment)
        self.assertEqual(get_cache_fresh_time(self.file_path).replace(microsecond=0), moment)

    def test_rewritten_near_other_midnight(self):
        """历史缓存若在别的日子的 0 点附近被重写，不能当作新鲜"""
        rewritten = datetime(2026, 8, 1, 0, 2)
        self._set_mtime(rewritten)
        # 该 mtime 紧邻「它自己那天」的 0 点：只看 mtime 的实现会误判为新鲜
        self.assertLessEqual(abs(rewritten - rewritten.replace(hour=0, minute=0, second=0)),
                             timedelta(hours=4))
        self.assertIsNone(get_cache_fresh_time(self.file_path))

    def test_missing_file(self):
        self.assertIsNone(get_cache_fresh_time(os.path.join(self.temp_dir, "not-exist.json")))


class TestStaleRankingFallback(unittest.TestCase):
    """目标日期缓存不新鲜时，榜单要回退到次日缓存里的 ranking 而不是它的 ranking"""

    TARGET_DATE = "2026-07-25"
    NEXT_DATE = "2026-07-26"
    BOARD_ID = "cache-fallback-test"

    def setUp(self):
        work_dir = os.path.join(os.path.dirname(__file__), "..")
        self.data_dir = os.path.join(work_dir, "data")
        self.target_path = os.path.join(self.data_dir, f"{self.BOARD_ID}-{self.TARGET_DATE}.json")
        self.next_path = os.path.join(self.data_dir, f"{self.BOARD_ID}-{self.NEXT_DATE}.json")
        self.config = Config(work_dir, {
            "handler": "Hydro", "credentials": None, "exclude_uid": [],
            "exclude_reg_date": "2000-01-01", "show_unrated": False, "data": "data",
            "url": "http://example.com/", "id": self.BOARD_ID, "board_name": "Cache Test Board",
        })
        # 目标日期缓存里只有两个人，次日缓存里多一个 carol，用于区分取到了哪份 ranking
        self._write_daily(self.target_path, {"alice": 5, "bob": 3})
        self._write_daily(self.next_path, {"alice": 7, "bob": 3, "carol": 1})
        rewritten = datetime(2026, 8, 1, 0, 2)  # 别的日子的 0 点附近 => 不新鲜
        os.utime(self.target_path, (rewritten.timestamp(), rewritten.timestamp()))

    def tearDown(self):
        for path in (self.target_path, self.next_path):
            if os.path.exists(path):
                os.remove(path)

    @staticmethod
    def _write_daily(path: str, accepted: dict[str, int]):
        users = list(accepted)
        submissions = [{
            "user": {"name": name, "uid": str(idx + 1), "register_at": 0},
            "score": 100, "verdict": "Accepted", "problem_id": f"p{idx}",
            "problem_name": f"Problem {idx}", "at": 1753459200 + idx,
        } for idx, name in enumerate(users)]
        rankings = [{
            "user": {"name": name, "uid": str(idx + 1), "register_at": 0},
            "accepted": str(cnt), "rank": str(idx + 1), "unrated": False,
        } for idx, (name, cnt) in enumerate(accepted.items())]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"submissions": submissions, "rankings": rankings}, f, ensure_ascii=False)

    def _rank_section(self, generator):
        for section in generator.section_content.section_bundle:
            if getattr(section, "str_header", None) and section.str_header.content == "训练榜单":
                return section

    def test_falls_back_to_next_day_cache(self):
        generator = MiscBoardGenerator(self.config, "full",
                                       os.path.join(self.data_dir, "logo.png"),
                                       date_string=self.TARGET_DATE)
        self.assertIsNone(generator._cache_fresh_time)
        section = self._rank_section(generator)
        self.assertEqual([item["str_uname"].content for item in section.section_render_materials],
                         ["alice", "bob", "carol"])
        self.assertIn("次日本地缓存", section.str_hint.content)
        generator.render()  # 回退分支能正常出图


class TestParseFullDate(unittest.TestCase):
    """--full 的日期参数在解析阶段校验并规范化"""

    def test_normalize_date(self):
        self.assertEqual(parse_full_date("2026-9-1"), "2026-09-01")

    def test_bare_full_keeps_const(self):
        self.assertEqual(parse_full_date(""), "")

    def test_invalid_date(self):
        for value in ("2026-7-5x", "2026-13-01", "昨天"):
            with self.subTest(value=value):
                self.assertRaises(argparse.ArgumentTypeError, parse_full_date, value)


if __name__ == '__main__':
    unittest.main()
