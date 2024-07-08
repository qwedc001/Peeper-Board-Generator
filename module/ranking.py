import json
import logging
import os

import requests
from lxml import etree
from module.config import Config
from module.structures import RankingData
from module.utils import headers, get_date_string


def fetch_rankings(config: Config) -> list[RankingData]:
    logging.info("开始获取排行榜记录")
    result = []
    page = 1
    while True:
        logging.debug(f'正在获取第{page}页的排行榜记录')
        url = config.get_config('url') + f'ranking?page={page}'
        response_html = etree.HTML(requests.get(url, headers=headers).text)
        if len(response_html.xpath('//div[@class="nothing-icon"]')) > 0:
            break
        for people in response_html.xpath('//table[@class="data-table"]/tbody//child::tr'):
            user_name = "".join(people.xpath("./td[@class='col--user']/span/a[contains(@class, "
                                             "'user-profile-name')]/text()")).strip()
            accepted = "".join(people.xpath("./td[@class='col--ac']/text()")).strip()
            rank = "".join(people.xpath("./td[@class='col--rank']/text()")).strip()
            uid = people.xpath("./td[@class='col--user']/span/a[contains(@class, 'user-profile-name')]/@href")[0].split(
                "/user/")[1]
            result.append(RankingData(user_name, accepted, uid, rank))
        page += 1
    return result


def load_ranking_json(config: Config, is_yesterday: bool) -> list[RankingData]:
    result = []
    ranking_file = f'ranking-{get_date_string(is_yesterday)}.json'
    ranking_file_path = os.path.join(config.work_dir, config.get_config('data'), ranking_file)
    data = []
    with open(ranking_file_path, 'r',encoding='utf-8') as f:
        data = json.load(f)
        f.close()
    for user in data:
        result.append(RankingData(user['user_name'], user['accepted'], user['uid'], user['rank']))
    return result


def save_ranking_json(config: Config, data: list[RankingData]):
    ranking_file = f'ranking-{get_date_string(False)}.json'
    ranking_file_path = os.path.join(config.work_dir, config.get_config('data'), ranking_file)
    with open(ranking_file_path, 'w',encoding='utf-8') as f:
        json.dump([user.__dict__ for user in data], f, ensure_ascii=False, indent=4)
        f.close()
    logging.info(f'排行榜记录已保存至 {ranking_file_path}')
