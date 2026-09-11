import tempfile
import unittest

from module.Hydro.entry import HydroHandler
from module.Hydro.ranking import fetch_rankings
from module.Hydro.tools import reload_stats
from module.Hydro.submission import fetch_submissions
from module.Hydro.user import fetch_user
from module.submission import *
from module.utils import *
from module.config import Configs

config = Configs(os.path.join(os.path.dirname(__file__), "..", "config.json")).get_configs()[0]
oj_url = config.get_config()["url"]


def ensure_session() -> None:
    """Hydro 的提交/榜单接口都要求登录，这里按需建立 session 并放回 config。"""
    if config.get_config().get("session") is None:
        HydroHandler(config).begin_session()


def load_submission_json() -> tuple[list[SubmissionData], list[SubmissionData]]:
    yesterday_json = open("submission_result_yesterday.json", "r", encoding="utf-8")
    today_json = open("submission_result_today.json", "r", encoding="utf-8")
    yesterday_submissions = json.load(yesterday_json)
    today_submissions = json.load(today_json)
    yesterday_json.close()
    today_json.close()
    submissions = []
    for submission in yesterday_submissions:
        submissions.append(SubmissionData(UserData(submission['user']['name'], submission['user']['uid'],
                                                   submission['user'].get('register_at', 0)),
                                          submission['score'], submission['verdict'], submission['problem_id'],
                                          submission['problem_name'], submission['at']))
    yesterday_submissions = submissions
    submissions = []
    for submission in today_submissions:
        submissions.append(SubmissionData(UserData(submission['user']['name'], submission['user']['uid'],
                                                   submission['user'].get('register_at', 0)),
                                          submission['score'], submission['verdict'], submission['problem_id'],
                                          submission['problem_name'], submission['at']))
    today_submissions = submissions
    return yesterday_submissions, today_submissions


class TestUtil(unittest.TestCase):

    def test_reload_rp(self):
        req_type = "rp"
        self.assertTrue(reload_stats(config, oj_url, req_type))

    def test_reload_problemStat(self):
        req_type = "problemStat"
        self.assertTrue(reload_stats(config, oj_url, req_type))


class TestSubmissionModule(unittest.TestCase):

    def test_0_fetch_submissions_yesterday(self):
        ensure_session()
        result = fetch_submissions(config, True)
        with open("submission_result_yesterday.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_1_fetch_submissions_today(self):
        ensure_session()
        result = fetch_submissions(config, False)
        with open("submission_result_today.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_2_get_first_ac(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_first_ac(yesterday_submissions), "today": get_first_ac(today_submissions)}
        with open("first_ac.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_2_hourly_ac(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_hourly_submissions(yesterday_submissions),
                  "today": get_hourly_submissions(today_submissions)}
        with open("hourly_ac.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_2_popular_problem(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_most_popular_problem(yesterday_submissions),
                  "today": get_most_popular_problem(today_submissions)}
        with open("popular_problem.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_2_classify_by_verdict(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": classify_by_verdict(yesterday_submissions),
                  "today": classify_by_verdict(today_submissions)}
        with open("classify_by_verdict.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)

    def test_2_rank_by_verdict(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": rank_by_verdict(yesterday_submissions),
                  "today": rank_by_verdict(today_submissions)}
        with open("rank_by_verdict.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(len(result) > 0)


class TestUserModule(unittest.TestCase):
    def test_fetch_user(self):
        # 在 config.json 中填入一个有 qq 号的用户来检验 infer_qq 模块是否正常
        uid = config.get_config().get("test", {}).get("user", {}).get("uid")
        if not uid:
            self.skipTest("config.json 中未配置 test.user.uid，无法指定用于 infer_qq 检查的用户")
        ensure_session()
        result = fetch_user(config, uid)
        with open("user.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        self.assertTrue(result.qq != "")


class TestStructure(unittest.TestCase):

    def test_daily_json_save(self):
        ensure_session()
        submission_data = fetch_submissions(config, False)
        ranking_data = fetch_rankings(config)
        daily_json = DailyJson(submission_data, ranking_data)
        save_json(config, daily_json)
        # save_json/load_json 使用的文件名规则为 {id}-{date}.json
        file_path = os.path.join(config.work_dir, config.get_config()["data"],
                                 f'{config.get_config()["id"]}-{get_date_string(False)}.json')
        self.assertTrue(os.path.exists(file_path))

    def test_daily_json_load(self):
        daily_json = load_json(config, False)
        self.assertTrue(daily_json is not None)


class TestLogin(unittest.TestCase):
    def test_login(self):
        handler = HydroHandler(config)
        credentials = config.get_config()["credentials"]
        session = handler.login(credentials)
        self.assertTrue(session is not None)


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


if __name__ == '__main__':
    unittest.main()
