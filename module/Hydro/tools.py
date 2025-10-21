import logging
import time

from module.config import Config
from module.Hydro.verdict import VERDICT_MAP
from module.utils import json_headers, fetch_url


def reload_stats(config: Config, oj_url: str, req_type: str):
    logging.info(f"正在重新加载 {req_type} 数据")
    url = oj_url + 'manage/script'
    rp_headers = json_headers.copy()
    if config.get_config()["session"] is None:
        raise Exception("登录信息无效，请重试")
    rp_headers['Cookie'] = (
        f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
        f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};'
    )
    rp_headers['Content-Type'] = 'application/json'
    data = f'{{"args":"","id":"{req_type}"}}'
    response_create_task = fetch_url(url, method='post', headers=rp_headers, data=data)
    record_id = response_create_task.json()["rid"]
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
    return True
