import json
import os
import tempfile
import time
import unittest

from module.config import Config
from module.Hydro.entry import HydroHandler
from module.structures import SubmissionData, UserData
from module.utils import get_date_string


class TestCalculateRankingNewUser(unittest.TestCase):
    """离线验证 calculate_ranking 对新用户的补建逻辑。"""

    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.work_dir, "data"), exist_ok=True)
        self.config = Config(self.work_dir, {
            "id": "test",
            "handler": "Hydro",
            "exclude_uid": [],
            "exclude_reg_date": "2020-01-01",
            "url": "https://example.com/",
        })

    def _write_yesterday_json(self, rankings):
        file_path = os.path.join(
            self.work_dir, "data", f"test-{get_date_string(True)}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"submissions": [], "rankings": rankings}, f,
                      ensure_ascii=False, indent=4)

    def _make_submission(self, uid, name, problem_id, register_at, offset):
        return SubmissionData(
            UserData(name, uid, register_at), 100, "Accepted", problem_id,
            f"problem-{problem_id}", int(time.time()) + 60 + offset)

    def test_new_user_is_added_and_counted(self):
        self._write_yesterday_json([
            {"user_name": "old", "accepted": "5", "uid": "1",
             "rank": 0, "unrated": False},
        ])
        submissions = [
            self._make_submission("2", "new", "A", 1700000000, 0),
            self._make_submission("2", "new", "A", 1700000000, 1),  # 重复 AC，应忽略
            self._make_submission("2", "new", "B", 1700000000, 2),
            self._make_submission("1", "old", "C", 1700000000, 3),
        ]

        rankings = HydroHandler(self.config).calculate_ranking(submissions)
        ranking_by_uid = {ranking.uid: ranking for ranking in rankings}

        self.assertEqual(ranking_by_uid["1"].accepted, "6")
        self.assertEqual(ranking_by_uid["2"].accepted, "2")
        self.assertFalse(ranking_by_uid["2"].unrated)
        self.assertEqual([ranking.uid for ranking in rankings], ["1", "2"])

    def test_new_user_unrated_rules(self):
        self.config.get_config()["exclude_uid"] = [3]
        self.config.get_config()["exclude_reg_date"] = "2026-01-01"
        self._write_yesterday_json([])
        submissions = [
            self._make_submission("2", "recent", "A", 1800000000, 0),
            self._make_submission("3", "excluded_by_uid", "B", 1800000000, 1),
            self._make_submission("4", "old_reg", "C", 1500000000, 2),
        ]

        rankings = HydroHandler(self.config).calculate_ranking(submissions)
        ranking_by_uid = {ranking.uid: ranking for ranking in rankings}

        self.assertFalse(ranking_by_uid["2"].unrated)
        self.assertTrue(ranking_by_uid["3"].unrated)
        self.assertTrue(ranking_by_uid["4"].unrated)

    def test_user_data_from_json_falls_back_to_zero(self):
        user = UserData.from_json({"name": "legacy", "uid": "7"})
        self.assertEqual(user.register_at, 0)


if __name__ == "__main__":
    unittest.main()