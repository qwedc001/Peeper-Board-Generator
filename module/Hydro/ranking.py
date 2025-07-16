import logging
from datetime import datetime

import requests
from dateutil.parser import isoparse
from lxml import etree
from module.config import Config
from module.structures import RankingData
from module.utils import headers, json_headers


def fetch_rankings(config: Config) -> list[RankingData]:
    logging.info("开始获取排行榜记录")
    result = []
    page = 1
    if config.get_config()["session"] is not None:
        headers['Cookie'] = (f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
                             f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};')
    exclude_uid: list = config.get_config()["exclude_uid"]
    exclude_date = config.get_config()["exclude_reg_date"]
    exclude_time = datetime.strptime(exclude_date, "%Y-%m-%d").timestamp()
    logging.info(f"排除规则：uid 在列表{exclude_uid}，注册时间早于{exclude_date}(换算为时间戳为{exclude_time})的用户")
    while True:
        logging.debug(f'正在爬取第 {page} 页的排行榜记录')
        url = config.get_config()["url"] + f'ranking?page={page}'
        response_html = etree.HTML(requests.get(url, headers=headers).text)
        response_json = requests.get(url, headers=json_headers).json()['udocs']
        reg_date_json = {str(user['_id']): user['regat'] for user in response_json}
        if len(response_html.xpath('//div[@class="nothing-icon"]')) > 0:
            break
        for people in response_html.xpath('//table[@class="data-table"]/tbody//child::tr')[1:]:
            user_name = "".join(people.xpath("./td[@class='col--user']/span/a[contains(@class, "
                                             "'user-profile-name')]/text()")).strip()
            badge = "".join(people.xpath("./td[@class='col--user']/span/span[contains(@class, "
                                         "'user-profile-badge')]/text()")).strip()
            accepted = "".join(people.xpath("./td[@class='col--ac']/text()")).strip()
            rank = "".join(people.xpath("./td[@class='col--rank']/text()")).strip()
            uid = people.xpath("./td[@class='col--user']/span/a[contains(@class, 'user-profile-name')]/@href")[0].split(
                "/user/")[1]
            unrated = False
            if int(uid) in exclude_uid:
                unrated = True
                logging.debug(f"用户 {user_name} 已被 uid 规则排除。")
            reg_time = isoparse(reg_date_json[uid]).timestamp()
            if exclude_time > reg_time:
                unrated = True
                logging.debug(f"用户 {user_name} 注册时间早于 {exclude_date} ，已被排除。")
            result.append(RankingData(user_name, accepted, uid, rank, unrated))
        page += 1
    return result
