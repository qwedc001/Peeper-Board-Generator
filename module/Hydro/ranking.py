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
    exclude_uid: list = config.get_config("extras")["Hydro"]["excludeUid"]
    exclude_date = config.get_config("extras")["Hydro"]["excludeRegDate"]
    exclude_time = datetime.strptime(exclude_date, "%Y-%m-%d").timestamp()
    logging.info(f"排除规则：uid 在列表{exclude_uid}，注册时间早于{exclude_date}(换算为时间戳为{exclude_time})的用户")
    while True:
        logging.debug(f'正在获取第{page}页的排行榜记录')
        url = config.get_config('url') + f'ranking?page={page}'
        response_html = etree.HTML(requests.get(url, headers=headers).text)
        response_json = requests.get(url, headers=json_headers).json()['udocs']
        reg_date_json = {str(user['_id']): user['regat'] for user in response_json}
        if len(response_html.xpath('//div[@class="nothing-icon"]')) > 0:
            break
        for people in response_html.xpath('//table[@class="data-table"]/tbody//child::tr'):
            user_name = "".join(people.xpath("./td[@class='col--user']/span/a[contains(@class, "
                                             "'user-profile-name')]/text()")).strip()
            accepted = "".join(people.xpath("./td[@class='col--ac']/text()")).strip()
            rank = "".join(people.xpath("./td[@class='col--rank']/text()")).strip()
            uid = people.xpath("./td[@class='col--user']/span/a[contains(@class, 'user-profile-name')]/@href")[0].split(
                "/user/")[1]
            unrated = False
            if int(uid) in exclude_uid:
                unrated = True
                logging.debug(f"用户 {user_name} 已被规则排除。")
            reg_time = isoparse(reg_date_json[uid]).timestamp()
            if exclude_time > reg_time:
                unrated = True
                logging.debug(f"用户 {user_name} 注册时间早于{exclude_date}，已被排除。")
            logging.debug(f"用户 {user_name} 的排名为 {rank}，已解决题目数为 {accepted}。{'该用户计入排行榜' if not unrated else '该用户已被排除。'}")
            logging.debug(f"注册时间为 {reg_time}，排除时间为 {exclude_time}")
            result.append(RankingData(user_name, accepted, uid, rank, unrated))
        page += 1
    return result
