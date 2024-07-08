import json
import os
from datetime import datetime, timedelta
from typing import Tuple
import requests
from module.config import Config
from module.structures import DailyJson, SubmissionData
from module.submission import rank_by_verdict, get_first_ac, classify_by_verdict, get_hourly_submissions, \
    get_most_popular_problem, count_users_submitted

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                  "Safari/537.36"
}
json_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                  "Safari/537.36",
    'Accept': 'application/json',
}


def get_qq_name(qq: str):
    url = 'https://api.usuuu.com/qq/' + qq
    res = requests.get(url, headers)
    if res.json()['code'] == 200:
        return res.json()['data']['name']
    else:
        raise Exception("获取QQ昵称失败")


def get_yesterday_timestamp() -> Tuple[int, int]:
    yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999)
    return int(yesterday_start.timestamp()), int(yesterday_end.timestamp())


def get_today_timestamp() -> Tuple[int, int]:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now()
    return int(today_start.timestamp()), int(today_end.timestamp())


def get_date_string(is_yesterday: bool) -> str:
    today_timestamp = datetime.now().timestamp()
    if is_yesterday:
        today_timestamp -= 86400
    return datetime.fromtimestamp(today_timestamp).strftime('%Y-%m-%d')


def load_json(config: Config, is_yesterday: bool) -> DailyJson:
    json_file = f'daily-{get_date_string(is_yesterday)}.json'
    file_path = os.path.join(config.work_dir, config.get_config('data'), json_file)
    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)
        f.close()
    return DailyJson.from_json(content)


def save_json(config: Config, data: DailyJson):
    json_file = f'daily-{get_date_string(False)}.json'
    file_path = os.path.join(config.work_dir, config.get_config('data'), json_file)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        f.close()
