import logging
from typing import Dict, Union, Any

import requests
import time
from module.config import Config
from module.verdict import STATUS_VERDICT
from module.utils import json_headers
from module.structures import SubmissionData, UserData
from module.utils import get_today_timestamp, get_yesterday_timestamp
from dateutil.parser import isoparse


def fetch_submissions(config: Config, is_yesterday: bool) -> list[SubmissionData]:
    logging.info("开始获取提交记录")
    result = []
    if is_yesterday:
        logging.debug("获取昨日提交记录")
        time_start, time_end = get_yesterday_timestamp()
    else:
        logging.debug("获取今日提交记录")
        time_start, time_end = get_today_timestamp()
    out_of_date = False
    page = 1
    headers = json_headers
    headers['Cookie'] = f'sid={config.get_config("cookie")["sid"]};sid.sig={config.get_config("cookie")["sid_sig"]};'
    while not out_of_date:
        url = config.get_config('url') + f'record?all=1&page={page}'
        response_json = requests.get(url, headers=headers).json()
        record_json = response_json['rdocs']
        user_json = response_json['udict']
        problem_json = response_json['pdict']
        for submission in record_json:
            if submission['lang'] == '-':
                # 自测提交记录，不计入
                continue
            if "hackTarget" in submission:
                # hack记录，不计入
                continue
            submission_timestamp = isoparse(submission['judgeAt']).timestamp()
            if submission_timestamp > time_end:
                # 不在记录时域范围内
                continue
            if submission_timestamp < time_start:
                out_of_date = True
                break
            uid = str(submission['uid'])
            name = user_json[uid]['uname']
            user = UserData(name, uid)
            score = submission['score']
            verdict = STATUS_VERDICT[submission['status']]
            problem_name = problem_json[str(submission['pid'])]['title']
            at = int(submission_timestamp)
            result.append(SubmissionData(user, score, verdict, problem_name, at))
        page += 1
    return result


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
    for submission in submission_list:
        if submission.problem_name not in problem_dict:
            problem_dict[submission.problem_name] = 0
        problem_dict[submission.problem_name] += 1
    max_problem = max(problem_dict, key=problem_dict.get)
    return max_problem, problem_dict[max_problem]


def classify_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result = {
        "avg_score": 0,
        "ac_rate": 0.0,
        "verdicts": {}
    }
    for submission in submission_list:
        if submission.verdict not in result:
            result['verdicts'][submission.verdict] = 0
        result['verdicts'][submission.verdict] += 1
        result['avg_score'] += submission.score
        result['ac_rate'] += 1 if submission.verdict == 'Accepted' else 0
    result['avg_score'] /= len(submission_list)
    result['ac_rate'] /= len(submission_list)
    return result


def rank_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result: dict[Union[str, int], Union[dict[str, int], dict[str, int]]] = {} # 这一段是 PyCharm 自动加的类型提示
    for submission in submission_list:
        if submission.verdict not in result:
            result[submission.verdict] = {}
        if submission.user.name not in result[submission.verdict]:
            result[submission.verdict][submission.user.name] = 0
        result[submission.verdict][submission.user.name] += 1
    for verdict in result:
        result[verdict] = dict(sorted(result[verdict].items(), key=lambda x: x[1], reverse=True))
    return result
