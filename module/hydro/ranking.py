import logging
import requests
from lxml import etree
from module.config import Config
from module.structures import RankingData
from module.utils import headers


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
