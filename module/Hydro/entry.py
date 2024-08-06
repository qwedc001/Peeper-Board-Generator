import json
import logging
import os
import time

import requests
from requests import Session

from module.config import Config
from module.Hydro.tools import reload_stats
from module.structures import DailyJson, RankingData, SubmissionData
from module.Hydro.submission import fetch_submissions
from module.Hydro.ranking import fetch_rankings
from module.utils import save_json, get_date_string


class HydroHandler:

    def __init__(self, config: Config, url: str):
        self.config = config
        self.url = url

    def get_yesterday(self):
        logging.info("开始爬取昨日数据")
        reload_stats(self.config, self.url, "problemStat")
        reload_stats(self.config, self.url, "rp")
        ranking = fetch_rankings(self.config)
        daily = DailyJson(fetch_submissions(self.config, True), ranking)
        save_json(self.config, daily, True)

    def save_daily(self, mode: str):
        logging.info("开始保存 json 数据")
        logging.info("尝试登录获取新 Session")
        credentials = self.config.get_config("credentials")["Hydro"]
        if credentials is not None:
            session = self.login(credentials)
            self.config.set_config("session", session)
            logging.info("Session 获取成功")
        if mode == "full":  # 检查昨日榜单的json文件日期是否为今日，如果是则跳过执行
            json_file = f'daily-{get_date_string(True)}.json'
            if not os.path.exists(os.path.join(self.config.work_dir, self.config.get_config('data'), json_file)):
                self.get_yesterday()
                return
            file_timestamp = os.stat(
                os.path.join(self.config.work_dir, self.config.get_config('data'), json_file)).st_mtime
            if time.strftime("%Y-%m-%d", time.gmtime(file_timestamp)) == get_date_string(False):
                logging.info("昨日 json 数据已存在并且固定，跳过爬取")
                return
            else:
                self.get_yesterday()
        elif mode == "now":  # 检查昨日榜单文件是否生成
            json_file = f'daily-{get_date_string(True)}.json'
            file_path = os.path.join(self.config.work_dir, self.config.get_config('data'), json_file)
            if not os.path.exists(file_path):
                logging.info("昨日json数据不存在")
                self.get_yesterday()
            today_submissions = fetch_submissions(self.config, False)
            ranking = self.calculate_ranking(today_submissions)
            daily = DailyJson(today_submissions, ranking)
            save_json(self.config, daily, False)

    def login(self, credentials: dict) -> Session:
        with requests.Session() as session:
            session.post(f"{self.url}login", data=credentials)
            return session

    def calculate_ranking(self, submissions: list[SubmissionData]) -> list[RankingData]:
        logging.info("正在根据昨日排名和今日提交计算当前排名")
        json_file = f'daily-{get_date_string(True)}.json'
        file_path = os.path.join(self.config.work_dir, self.config.get_config('data'), json_file)
        ranking = DailyJson.from_json(json.load(open(file_path, "r", encoding="utf-8"))).rankings
        for submission in submissions:
            if submission.verdict == "Accepted":
                for rank in ranking:
                    if submission.user.uid == rank.uid:
                        rank.accepted = str(int(rank.accepted) + 1)
        # 根据新的accepted 数量重新排序
        ranking.sort(key=lambda x: x.accepted, reverse=True)
        for i in range(len(ranking)):
            ranking[i].rank = i
        return ranking

