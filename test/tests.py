import json
import unittest

from module.structures import SubmissionData, UserData
from module.submission import fetch_submissions, get_first_ac, get_hourly_submissions, get_most_popular_problem, \
    classify_by_verdict, rank_by_verdict
from module.user import fetch_user
from module.utils import *
from module.config import Config

config = Config("../config.json")
oj_url = config.get_config("url")


def load_submission_json() -> tuple[list[SubmissionData], list[SubmissionData]]:
    yesterday_json = open("submission_result_yesterday.json", "r", encoding="utf-8")
    today_json = open("submission_result_today.json", "r", encoding="utf-8")
    yesterday_submissions = json.load(yesterday_json)
    today_submissions = json.load(today_json)
    yesterday_json.close()
    today_json.close()
    submissions = []
    for submission in yesterday_submissions:
        submissions.append(SubmissionData(UserData(submission['user']['name'], submission['user']['uid']),
                                          submission['score'], submission['verdict'], submission['problem_name'],
                                          submission['at']))
    yesterday_submissions = submissions
    submissions = []
    for submission in today_submissions:
        submissions.append(SubmissionData(UserData(submission['user']['name'], submission['user']['uid']),
                                          submission['score'], submission['verdict'], submission['problem_name'],
                                          submission['at']))
    today_submissions = submissions
    return yesterday_submissions, today_submissions


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


class TestSubmissionModule(unittest.TestCase):
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

    def test_get_first_ac(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_first_ac(yesterday_submissions), "today": get_first_ac(today_submissions)}
        with open("first_ac.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)

    def test_hourly_ac(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_hourly_submissions(yesterday_submissions),
                  "today": get_hourly_submissions(today_submissions)}
        with open("hourly_ac.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)

    def test_popular_problem(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": get_most_popular_problem(yesterday_submissions),
                  "today": get_most_popular_problem(today_submissions)}
        with open("popular_problem.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)

    def test_classify_by_verdict(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": classify_by_verdict(yesterday_submissions),
                  "today": classify_by_verdict(today_submissions)}
        with open("classify_by_verdict.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)

    def test_rank_by_verdict(self):
        yesterday_submissions, today_submissions = load_submission_json()
        result = {"yesterday": rank_by_verdict(yesterday_submissions),
                  "today": rank_by_verdict(today_submissions)}
        with open("rank_by_verdict.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        self.assertTrue(len(result) > 0)


class TestUserModule(unittest.TestCase):
    def test_fetch_user(self):
        uid = config.get_config("test")['user']['uid']
        result = fetch_user(config, uid)
        with open("user.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
            f.close()
        # 在测试 json 中填入一个有 qq 号的用户来检验 infer_qq 模块是否正常
        self.assertTrue(result.qq != "")


if __name__ == '__main__':
    unittest.main()
