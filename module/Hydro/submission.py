import logging
import requests
from module.config import Config
from module.Hydro.verdict import STATUS_VERDICT
from module.utils import json_headers
from module.structures import SubmissionData, UserData
from module.utils import get_today_timestamp, get_yesterday_timestamp
from dateutil.parser import isoparse


def fetch_submissions(config: Config, is_yesterday: bool) -> list[SubmissionData]:
    time_str = "昨日" if is_yesterday else "今日"
    logging.info(f"开始获取{time_str}提交记录")
    result = []
    if is_yesterday:
        time_start, time_end = get_yesterday_timestamp()
    else:
        time_start, time_end = get_today_timestamp()
    out_of_date = False
    page = 1
    headers = json_headers
    if config.get_config()["session"] is not None:
        headers['Cookie'] = (f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
                             f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};')
    else:
        headers['Cookie'] = (f'sid={config.get_config()["session"]["sid"]};'
                             f'sid.sig={config.get_config()["session"]["sid_sig"]};')
    while not out_of_date:
        url = config.get_config()["url"] + f'record?all=1&page={page}'
        response_json = requests.get(url, headers=headers).json()
        record_json = response_json['rdocs']
        user_json = response_json['udict']
        problem_json = response_json['pdict']
        for submission in record_json:
            if submission['lang'] == '-' or ('contest' in submission
                                             and submission['contest'] == '000000000000000000000000'):
                # 自测提交记录，不计入
                continue
            if "hackTarget" in submission:
                # hack记录，不计入
                continue
            if "judgeAt" not in submission or submission['judgeAt'] is None:
                # pending or 异常数据，不计入
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
            # 保持与排行榜用户名显示一样的逻辑
            if 'displayName' in user_json[uid]:
                name = f"{user_json[uid]['displayName']} ({name})"
            user = UserData(name, uid)
            score = submission['score']
            verdict = STATUS_VERDICT[submission['status']]
            problem_id = str(submission['pid'])
            problem_name = problem_json[problem_id]['title']
            at = int(submission_timestamp)
            result.append(SubmissionData(user, score, verdict, problem_id, problem_name, at))
        page += 1
    return result
