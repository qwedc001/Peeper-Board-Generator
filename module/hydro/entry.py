import logging

from module.config import Config
from module.hydro.tools import reload_stats


class HydroHandler:

    def __init__(self, config: Config, url: str):
        self.config = config
        self.url = url

    def generate_full_rank(self, verdict: str):
        logging.debug(f'得到的 verdict 为 {verdict}')

        # 1.获取最新的榜单数据(刷新题目统计和rp)
        reload_stats(self.config, self.url, "problemStat")
        reload_stats(self.config, self.url, "rp")

        # TODO: 2.爬取 rank 榜单

    def generate_now_rank(self, verdict: str):
        logging.debug(f'得到的 verdict 为 {verdict}')

        # 1.获取最新的榜单数据(刷新题目统计和rp)
        reload_stats(self.config, self.url, "problemStat")
        reload_stats(self.config, self.url, "rp")

        # TODO: 2.爬取 rank 榜单
