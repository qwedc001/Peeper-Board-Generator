import logging

import requests

from module.config import Config
from module.Hydro.tools import reload_stats
from module.structures import DailyJson
from module.Hydro.submission import fetch_submissions
from module.Hydro.ranking import fetch_rankings
from module.utils import save_json


class HydroHandler:

    def __init__(self, config: Config, url: str):
        self.config = config
        self.url = url

    def save_daily(self):
        logging.info("开始保存今日榜单")
        logging.info("尝试登录获取新 Session")
        credentials = self.config.get_config("credentials")["Hydro"]
        if credentials is not None:
            session = self.login(credentials)
            self.config.set_config("session", session)
            logging.info("Session 获取成功")
        reload_stats(self.config, self.url, "problemStat")
        reload_stats(self.config, self.url, "rp")
        daily = DailyJson(fetch_submissions(self.config, False), fetch_rankings(self.config))
        save_json(self.config, daily, False)
        daily = DailyJson(fetch_submissions(self.config, True), fetch_rankings(self.config))
        save_json(self.config, daily, True)

    def login(self, credentials: dict):
        with requests.Session() as session:
            session.post(f"{self.url}login", data=credentials)
            return session
