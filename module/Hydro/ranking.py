import logging
from datetime import datetime

from dateutil.parser import isoparse
from lxml import etree

from module.config import Config
from module.structures import RankingData
from module.utils import json_headers, fetch_url


def fetch_rankings(config: Config) -> list[RankingData]:
    logging.info("开始获取排行榜记录")
    result = []
    page = 1
    ranking_json_headers = json_headers.copy()
    if "session" not in config.get_config() or config.get_config()["session"] is None:
        raise Exception("登录信息无效，请重试")
    ranking_json_headers['Cookie'] = (
        f'sid={config.get_config()["session"].cookies.get_dict()["sid"]};'
        f'sid.sig={config.get_config()["session"].cookies.get_dict()["sid.sig"]};'
    )
    ranking_raw_headers = {'Cookie': ranking_json_headers['Cookie']}
    exclude_uid: list = config.get_config()["exclude_uid"]
    exclude_date = config.get_config()["exclude_reg_date"]
    exclude_time = datetime.strptime(exclude_date, "%Y-%m-%d").timestamp()
    logging.info(f"排除规则：uid 在列表 {exclude_uid} 中，或注册时间早于 {exclude_date}（换算为时间戳为 {exclude_time}）的用户")
    current_rank = 0
    while True:
        logging.debug(f'正在爬取第 {page} 页的排行榜记录')
        url = config.get_config()["url"] + f'ranking?page={page}'
        response_html = etree.HTML(fetch_url(url, method='get', headers=ranking_raw_headers).text)
        response_json = fetch_url(url, method='get', headers=ranking_json_headers).json()['udocs']
        user_json = {str(user['_id']): user for user in response_json}
        if len(response_html.xpath('//div[@class="nothing-icon"]')) > 0:
            break
        ranking_people = response_html.xpath('//table[@class="data-table"]/tbody//child::tr')
        # 检查第一个是不是自己：即第二名为本页实际的第一名
        if len(ranking_people) >= 2:
            second_rank = "".join(ranking_people[1].xpath("./td[@class='col--rank']/text()")).strip()
            if int(second_rank) == current_rank + 1:
                ranking_people = ranking_people[1:]  # 排除自己
        for people in ranking_people:
            accepted = "".join(people.xpath("./td[@class='col--ac']/text()")).strip()
            rank = "".join(people.xpath("./td[@class='col--rank']/text()")).strip()
            uid = people.xpath("./td[@class='col--user']/span/a[contains(@class, 'user-profile-name')]/@href")[0].split(
                "/user/")[1]
            user_name = user_json[uid]['uname']
            if 'displayName' in user_json[uid]:
                user_name = f"{user_json[uid]['displayName']} ({user_name})"
            unrated = False
            if int(uid) in exclude_uid:
                unrated = True
                logging.debug(f"用户 {user_name} 已被 uid 规则排除。")
            reg_time = isoparse(user_json[uid]['regat']).timestamp()
            if exclude_time > reg_time:
                unrated = True
                logging.debug(f"用户 {user_name} 注册时间早于 {exclude_date}，已被排除。")
            result.append(RankingData(user_name, accepted, uid, rank, unrated))
            current_rank = max(current_rank, int(rank))
        page += 1
    return result
