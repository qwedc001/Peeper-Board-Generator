import difflib
import json
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Tuple

import requests

from module.config import Config
from module.handler import BasicHandler
from module.structures import DailyJson

default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

# 显式只接受 json 返回, 对 Hydro 有效
json_headers = {
    'Accept': 'application/json',
}


def fetch_url(url: str, method: str = 'post', headers: dict | None = None,
              accept_codes: list[int] | None = None,
              timeout: float | tuple[float, float] = (5, 15),
              session: requests.Session | None = None, **kwargs) -> requests.Response:
    if accept_codes is None:
        accept_codes = [200]
    method = method.lower()
    if method not in ('post', 'get'):
        raise ValueError("不支持除 'post' 和 'get' 以外的其他连接方法")
    try:
        current_headers = default_headers.copy()
        if headers is not None:
            current_headers.update(headers)
        env = session if session is not None else requests
        if method == 'post':
            response = env.post(url, headers=current_headers, timeout=timeout, **kwargs)
        else:
            response = env.get(url, headers=current_headers, timeout=timeout, **kwargs)
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"无法连接到 {url}: {e}") from e
    code = response.status_code
    if code not in accept_codes:
        raise ConnectionError(f"无法连接到 {url}, 代码 {code}")
    return response


def fuzzy_search_user(config: Config, name: str, handler: BasicHandler):
    try:
        load_json(config, False)
    except FileNotFoundError:
        logging.info("未找到用户排名文件，正在进行更新")
        handler.save_daily("now")
    finally:
        data = load_json(config, False)
    
    # 首先在排行榜中搜索
    rankings = data.rankings
    res = difflib.get_close_matches(name, [ranking.user_name for ranking in rankings], cutoff=0.4, n=1)
    if len(res) > 0:
        for ranking in rankings:
            if ranking.user_name == res[0]:
                return handler.fetch_user(ranking.uid)
    
    # 如果在排行榜中未找到，在今日提交中搜索
    submissions = data.submissions
    submission_users = {submission.user.uid: submission.user.name for submission in submissions}
    res = difflib.get_close_matches(name, list(submission_users.values()), cutoff=0.4, n=1)
    if len(res) > 0:
        for uid, user_name in submission_users.items():
            if user_name == res[0]:
                return handler.fetch_user(uid)
    
    return "未找到用户"


def search_user_by_uid(uid: str, handler: BasicHandler):
    return handler.fetch_user(uid)  # 留给 handler 判断 uid 是否存在


def get_yesterday_timestamp() -> Tuple[int, int]:
    yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999)
    return int(yesterday_start.timestamp()), int(yesterday_end.timestamp())


def get_today_timestamp() -> Tuple[int, int]:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now()
    return int(today_start.timestamp()), int(today_end.timestamp())


def rand_tips(config: Config):
    # 构建列表
    tips_all = []
    tip_files = [os.path.join(config.work_dir, "data", "tips.json"), os.path.join(config.work_dir, "data", "tips.json")]
    for file in tip_files:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                tips = json.load(f)
                for section in tips:
                    for tip in section['tips']:
                        tips_all.append(tip)
                f.close()
    return random.choice(tips_all)


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


def performance_test(func):
    def wrapper(*args, **kwargs):
        start = datetime.now()
        result = func(*args, **kwargs)
        flag = False
        for item in args:
            if isinstance(item, Config):
                statistic_file = item.get_config()['statistic_file']
                logging.debug(statistic_file)
                if not statistic_file.closed:
                    statistic_file.write(
                        f"[{item.get_config()['id']}][{func.__name__}] 执行用时 {datetime.now() - start}\n")
                    logging.debug("已写入性能信息")
                    flag = True
                else:
                    logging.debug("性能测试文件已关闭")
        if not flag:
            print(f"[{func.__name__}] 执行用时 {datetime.now() - start}")
        return result

    return wrapper
