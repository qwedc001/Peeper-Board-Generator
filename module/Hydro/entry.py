import datetime
import json
import logging
import os

import requests
from requests import Session

from module.Hydro.user import fetch_user
from module.config import Config
from module.Hydro.tools import reload_stats
from module.handler import BasicHandler
from module.structures import DailyJson, RankingData, SubmissionData
from module.Hydro.submission import fetch_submissions
from module.Hydro.ranking import fetch_rankings
from module.utils import save_json, get_date_string, load_json


class HydroHandler(BasicHandler):

    def __init__(self, config: Config, url: str):
        super().__init__("HydroHandler")
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
        credentials = self.config.get_config()["credentials"]
        if credentials is not None:
            session = self.login(credentials)
            self.config.set_config("session", session)
            logging.info("Session 获取成功")
        if mode == "full":  # 检查昨日榜单的json文件日期是否为今日，如果是则跳过执行
            json_file = f'{self.config.get_config()["file_prefix"]}-{get_date_string(True)}.json'
            if not os.path.exists(os.path.join(self.config.work_dir, "data", json_file)):
                logging.info(f"昨日json数据{json_file}不存在")
                self.get_yesterday()
            file_timestamp = os.stat(
                os.path.join(self.config.work_dir, "data", json_file)).st_mtime

            logging.info(
                f"{json_file}文件最后修改时间为 {datetime.datetime.fromtimestamp(file_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            if datetime.datetime.fromtimestamp(file_timestamp).strftime('%Y-%m-%d') == get_date_string(False):
                logging.info("昨日 json 数据已固定，跳过爬取")
            else:
                self.get_yesterday()
        elif mode == "now":  # 检查昨日榜单文件是否生成
            json_file = f'{self.config.get_config()["file_prefix"]}-{get_date_string(True)}.json'
            file_path = os.path.join(self.config.work_dir, "data", json_file)
            if not os.path.exists(file_path):
                logging.info("昨日json数据不存在")
                self.get_yesterday()
        logging.info("重载今日数据")
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
        json_file = f'{self.config.get_config()["file_prefix"]}-{get_date_string(True)}.json'
        file_timestamp = os.stat(
            os.path.join(self.config.work_dir, "data", json_file)).st_mtime
        file_path = os.path.join(self.config.work_dir, "data", json_file)
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        ranking = DailyJson.from_json(content).rankings
        for submission in submissions:
            if submission.at < file_timestamp:
                continue
            if submission.verdict == "Accepted":
                for rank in ranking:
                    if submission.user.uid == rank.uid:
                        rank.accepted = str(int(rank.accepted) + 1)
        # 根据新的accepted 数量重新排序
        ranking.sort(key=lambda x: x.accepted, reverse=True)
        for i in range(len(ranking)):
            ranking[i].rank = i
        return ranking

    def fetch_user(self, uid: str):
        logging.info(f"正在获取用户 {uid} 的信息")
        user = fetch_user(self.config, uid)
        result_text = f'用户 {user.name} 的信息如下：\n' \
                      f'用户邮箱：{user.mail}\n' \
                      f'用户QQ：{user.qq}\n' \
                      f'用户QQ昵称：{user.qq_name}\n' \
                      f'用户状态：{user.status}\n' \
                      f'用户进度：{user.progress}\n' \
                      f'用户描述：{user.description}\n'
        submission_info = [submission for submission in load_json(self.config, False).submissions if
                           submission.user.uid == uid]
        result_text += f'用户今日提交信息：\n'
        total_submissions = 0
        avg_score = 0
        ac_rate = 0
        for submission in submission_info:
            total_submissions += 1
            avg_score += submission.score
            if submission.verdict == "Accepted":
                ac_rate += 1
        if total_submissions != 0:
            result_text += f'总提交次数：{total_submissions}\n' \
                       f'平均分数：{avg_score / total_submissions}\n' \
                       f'AC率：{ac_rate / total_submissions * 100}%\n'
        else:
            result_text += f'用户今日暂无提交。\n'
        return result_text
