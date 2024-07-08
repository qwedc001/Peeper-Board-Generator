import logging
import requests
from module.config import Config
from module.hydro.verdict import STATUS_VERDICT
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
