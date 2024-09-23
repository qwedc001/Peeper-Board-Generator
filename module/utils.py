import difflib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Tuple
import requests

from module.config import Config
from module.handler import BasicHandler
from module.structures import DailyJson

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


def fuzzy_search_user(config: Config, name: str, handler: BasicHandler):
    try:
        load_json(config, False)
    except FileNotFoundError:
        logging.info("未找到用户排名文件，正在进行更新")
        handler.save_daily("now")
    finally:
        data = load_json(config, False)
    rankings = data.rankings
    res = difflib.get_close_matches(name, [ranking.user_name for ranking in rankings], cutoff=0.4, n=1)
    if len(res) > 0:
        for ranking in rankings:
            if ranking.user_name == res[0]:
                return handler.fetch_user(ranking.uid)
    else:
        return "未找到用户"


def search_user_by_uid(config: Config, uid: str, handler: BasicHandler):
    try:
        load_json(config, False)
    except FileNotFoundError:
        logging.info("未找到用户排名文件，正在进行更新")
        handler.save_daily("now")
    finally:
        data = load_json(config, False)
    rankings = data.rankings
    for ranking in rankings:
        if ranking.uid == uid:
            return handler.fetch_user(ranking.uid)
    return "未找到用户"


def get_yesterday_timestamp() -> Tuple[int, int]:
    yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999)
    return int(yesterday_start.timestamp()), int(yesterday_end.timestamp())


def get_today_timestamp() -> Tuple[int, int]:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now()
    return int(today_start.timestamp()), int(today_end.timestamp())


def get_date_string(is_yesterday: bool, split: str = '-') -> str:
    today_timestamp = datetime.now().timestamp()
    if is_yesterday:
        today_timestamp -= 86400
    return datetime.fromtimestamp(today_timestamp).strftime(f"%Y{split}%m{split}%d")


def load_json(config: Config, is_yesterday: bool) -> DailyJson:
    json_file = f'{config.get_config()["id"]}-{get_date_string(is_yesterday)}.json'
    file_path = os.path.join(config.work_dir, "data", json_file)
    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)
        f.close()
    return DailyJson.from_json(content)


def save_json(config: Config, data: DailyJson, is_yesterday: bool = False):
    json_file = f'{config.get_config()["id"]}-{get_date_string(is_yesterday)}.json'
    file_path = os.path.join(config.work_dir, "data", json_file)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, default=lambda o: o.__dict__, ensure_ascii=False, indent=4))
        f.close()
