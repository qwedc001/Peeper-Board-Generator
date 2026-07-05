import datetime
import json
import logging
import os
import re
import time

from module.config import Config
from module.Hydro.verdict import VERDICT_MAP
from module.utils import json_headers, fetch_url


def pass_sudo(config: Config, oj_url: str):
    logging.info("正在尝试通过 sudo 验证")
    url = oj_url + 'user/sudo'
    sudo_headers = json_headers.copy()
    if "session" not in config.get_config() or config.get_config()["session"] is None:
        raise Exception("登录信息无效，请重试")
    sudo_headers['Cookie'] = (
        f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
        f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};'
    )
    sudo_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    data = {'password': config.get_config()["credentials"]["password"]}
    fetch_url(url, method='post', headers=sudo_headers, data=data)


def truncate_oj_url(oj_url: str):
    """去掉 oj_url 里的域后缀"""
    pattern = r'/d/[^/]*/?'
    matches = list(re.finditer(pattern, oj_url))
    if matches:
        last = matches[-1]
        return oj_url[:last.start()] + oj_url[last.end():]
    return oj_url


def check_reload_cache(config: Config, oj_url: str, req_type: str) -> bool:
    """检查当天是否已经成功重载"""
    real_oj_url = truncate_oj_url(oj_url)
    file_path = os.path.join(config.work_dir, "data", 'reload_cache.json')
    content = {}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    if real_oj_url in content and req_type in content[real_oj_url]:
        last_reload_time = content[real_oj_url][req_type]
        current_time = datetime.datetime.now().timestamp()
        last_date = datetime.datetime.fromtimestamp(last_reload_time).date()
        current_date = datetime.datetime.fromtimestamp(current_time).date()
        if current_date <= last_date:
            return True
    return False


def save_reload_cache(config: Config, oj_url: str, req_type: str):
    real_oj_url = truncate_oj_url(oj_url)
    file_path = os.path.join(config.work_dir, "data", 'reload_cache.json')
    content = {}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    if real_oj_url not in content:
        content[real_oj_url] = {}
    content[real_oj_url][req_type] = datetime.datetime.now().timestamp()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=4)


def reload_stats(config: Config, oj_url: str, req_type: str) -> bool:
    if check_reload_cache(config, oj_url, req_type):
        logging.info(f"当天已重载 {req_type} 数据，跳过重载")
        return True
    logging.info(f"正在重新加载 {req_type} 数据")

    url = oj_url + 'manage/script'
    rp_headers = json_headers.copy()
    if "session" not in config.get_config() or config.get_config()["session"] is None:
        raise Exception("登录信息无效，请重试")
    rp_headers['Cookie'] = (
        f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
        f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};'
    )
    rp_headers['Content-Type'] = 'application/json'
    data = f'{{"args":"","id":"{req_type}"}}'

    response_create_task = fetch_url(url, method='post', headers=rp_headers, data=data).json()
    if 'rid' not in response_create_task and 'user/sudo' in response_create_task["url"]:
        # 需要通过 sudo 校验
        pass_sudo(config, oj_url)
        response_create_task = fetch_url(url, method='post', headers=rp_headers, data=data).json()

    record_id = response_create_task["rid"]
    logging.debug(f'截取到 record id：{record_id}，类型：{req_type}')
    start_time = time.time()
    status = "Started"
    while not status == VERDICT_MAP["Accepted"]:
        if time.time() - start_time > 60:
            logging.error(f'请求刷新 {req_type} 时超时(60s)')
            raise Exception("请求刷新时超时")
        time.sleep(1)
        response_get_status = fetch_url(oj_url + f'record/{record_id}', method='get', headers=rp_headers)
        status = response_get_status.json()["rdoc"]["status"]
        logging.debug(f'当前 {req_type} 状态为：{status}')
    logging.info(f'重新加载 {req_type} 数据完成')

    save_reload_cache(config, oj_url, req_type)
    logging.debug(f'已缓存重载 {req_type} 数据的时间')
    return True
