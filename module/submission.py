import logging
import time
from typing import Union

from module.structures import SubmissionData, UserData


def get_first_ac(submission_list: list[SubmissionData]) -> SubmissionData:
    for submission in submission_list[::-1]:
        if submission.verdict == 'Accepted':
            return submission
    return SubmissionData(UserData("好像今天没有人AC", "-1"), 0, "Wait WHAT", "Never gonna give you up", 114514)


def get_hourly_submissions(submission_list: list[SubmissionData]) -> dict:
    result = {}
    for i in range(24):
        result[str(i)] = [0, 0]
    for submission in submission_list:
        hour = time.localtime(submission.at).tm_hour
        if submission.verdict == 'Accepted':
            result[str(hour)][0] += 1
        result[str(hour)][1] += 1
    # 0: AC, 1: 总数
    for i in range(24):
        if result[str(i)][1] == 0:
            result[str(i)][0] = 0
        else:
            result[str(i)][0] /= result[str(i)][1]
    # 0: AC 率, 1: 总数
    return result


def get_most_popular_problem(submission_list: list[SubmissionData]) -> tuple[str, int]:
    problem_dict = {}
    submission_user_dict = {}
    for submission in submission_list:
        if submission.problem_name not in problem_dict:
            problem_dict[submission.problem_name] = 0
            submission_user_dict[submission.problem_name] = [submission.user.name]
        if submission.user.name not in submission_user_dict[submission.problem_name]:
            problem_dict[submission.problem_name] += 1
            submission_user_dict[submission.problem_name].append(submission.user.name)
            logging.debug(f"检测到新提交用户{submission.user.name}，题目{submission.problem_name}，已记录。")
        else:
            logging.debug(f"检测到重复提交用户{submission.user.name}，题目{submission.problem_name}，已忽略。")
    max_problem = max(problem_dict, key=problem_dict.get)
    return max_problem, problem_dict[max_problem]


def classify_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result = {
        "avg_score": 0,
        "ac_rate": 0.0,
        "verdicts": {}
    }
    for submission in submission_list:
        if submission.verdict not in result['verdicts']:
            result['verdicts'][submission.verdict] = 0
        result['verdicts'][submission.verdict] += 1
        result['avg_score'] += submission.score
        result['ac_rate'] += 1 if submission.verdict == 'Accepted' else 0
    result['avg_score'] /= len(submission_list)
    result['ac_rate'] /= len(submission_list)
    return result


def rank_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result: dict[Union[str, int], Union[dict[str, int], dict[str, int]]] = {}  # 这一段是 PyCharm 自动加的类型提示
    for submission in submission_list:
        if submission.verdict not in result:
            result[submission.verdict] = {}
        if submission.user.name not in result[submission.verdict]:
            result[submission.verdict][submission.user.name] = 0
        result[submission.verdict][submission.user.name] += 1
    for verdict in result:
        result[verdict] = dict(sorted(result[verdict].items(), key=lambda x: x[1], reverse=True))
    return result


def count_users_submitted(submission_list: list[SubmissionData]) -> int:
    return len(set([submission.user.name for submission in submission_list]))
