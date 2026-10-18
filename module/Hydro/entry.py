import datetime
import json
import logging
import os
import re

import pixie
import requests

from module.Hydro.user import fetch_user
from module.board.user_card import UserCardGenerator, UserCardInfo, UserCardSection, render_user_notice
from module.config import Config
from module.Hydro.tools import reload_stats
from module.handler import BasicHandler
from module.structures import DailyJson, RankingData, SubmissionData
from module.Hydro.submission import fetch_submissions, fetch_recent_submissions
from module.Hydro.ranking import fetch_rankings, is_unrated_user
from module.utils import save_json, get_date_string, load_json, fetch_url, get_site_icon_url


class HydroHandler(BasicHandler):

    def __init__(self, config: Config):
        super().__init__("HydroHandler")
        self.config = config
        self.url = self.config.get_config()['url']
        self.reloaded_stats = False

    def reload_all(self):
        if not self.reloaded_stats:
            logging.info("正在重载 Hydro 的统计数据")
            reload_stats(self.config, self.url, "problemStat")
            reload_stats(self.config, self.url, "rp")
            self.reloaded_stats = True

    def begin_session(self):
        logging.info("尝试登录获取新 Session")
        credentials = self.config.get_config()["credentials"]
        if credentials is not None:
            session = self.login(credentials)
            self.config.set_config("session", session)
            logging.info("Session 获取成功")

    def get_yesterday(self):
        logging.info("开始爬取昨日数据")
        self.reload_all()
        ranking = fetch_rankings(self.config)
        daily = DailyJson(fetch_submissions(self.config, True), ranking)
        save_json(self.config, daily, True)

    def save_daily(self, mode: str):
        logging.info("开始保存 json 数据")
        self.begin_session()
        if mode == "full":  # 检查昨日榜单的json文件日期是否为今日，如果是则跳过执行
            json_file = f'{self.config.get_config()["id"]}-{get_date_string(True)}.json'
            if not os.path.exists(os.path.join(self.config.work_dir, "data", json_file)):
                logging.info(f"昨日 json 数据 {json_file} 不存在")
                self.get_yesterday()
            file_timestamp = os.stat(
                os.path.join(self.config.work_dir, "data", json_file)).st_mtime

            logging.info(
                f"{json_file} 文件最后修改时间为 {datetime.datetime.fromtimestamp(file_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            if datetime.datetime.fromtimestamp(file_timestamp).strftime('%Y-%m-%d') == get_date_string(False):
                logging.info("昨日 json 数据已固定，跳过爬取")
            else:
                self.get_yesterday()
        elif mode == "now":  # 检查昨日榜单文件是否生成
            json_file = f'{self.config.get_config()["id"]}-{get_date_string(True)}.json'
            file_path = os.path.join(self.config.work_dir, "data", json_file)
            if not os.path.exists(file_path):
                logging.info("昨日 json 数据不存在")
                self.get_yesterday()
        logging.info("重载今日数据")
        # 为降低时间复杂度，重载今日数据不需要刷新 rp 和 problemStat，后续会根据昨日排名和今日提交计算出
        today_submissions = fetch_submissions(self.config, False)
        ranking = self.calculate_ranking(today_submissions)
        daily = DailyJson(today_submissions, ranking)
        save_json(self.config, daily, False)

    def login(self, credentials: dict) -> requests.Session:
        session = requests.Session()
        fetch_url(f"{self.url}login", method='post', data=credentials,
                  session=session, allow_redirect=True)
        return session

    def calculate_ranking(self, submissions: list[SubmissionData]) -> list[RankingData]:
        logging.info("正在根据昨日排名和今日提交计算当前排名")
        json_file = f'{self.config.get_config()["id"]}-{get_date_string(True)}.json'
        file_timestamp = os.stat(
            os.path.join(self.config.work_dir, "data", json_file)).st_mtime
        file_path = os.path.join(self.config.work_dir, "data", json_file)
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        ranking = DailyJson.from_json(content).rankings
        
        # 获取当前配置中的排除规则
        exclude_uid: list = self.config.get_config()["exclude_uid"]
        exclude_time = datetime.datetime.strptime(
            self.config.get_config()["exclude_reg_date"], "%Y-%m-%d").timestamp()
        
        # 按当前配置重新判定所有用户的 unrated 状态。
        for rank in ranking:
            if rank.user.register_at > 0:
                rank.unrated = is_unrated_user(rank.user.uid, rank.user.register_at,
                                               exclude_uid, exclude_time)
            else:
                rank.unrated |= int(rank.user.uid) in exclude_uid  # fallback
        
        ranking_by_uid = {rank.uid: rank for rank in ranking}
        problem_ac_list: list[tuple[str, str]] = []  # uid, pid
        for submission in submissions:
            if submission.at < file_timestamp or submission.verdict != "Accepted":
                continue
            if (submission.user.uid, submission.problem_id) in problem_ac_list:
                continue  # 排除同一道题重复ac
            problem_ac_list.append((submission.user.uid, submission.problem_id))
            rank = ranking_by_uid.get(submission.user.uid)
            if rank is None:
                # 新用户不会被昨日的 ranking 收录，需要根据今日提交补建记录
                unrated = is_unrated_user(submission.user.uid,
                                          submission.user.register_at,
                                          exclude_uid, exclude_time)
                rank = RankingData(submission.user, "0", str(len(ranking)), unrated)
                ranking.append(rank)
                ranking_by_uid[submission.user.uid] = rank
                logging.info(f"检测到新用户 {submission.user.name} "
                             f"(UID {submission.user.uid})，已补入今日榜单。")
            rank.accepted = str(int(rank.accepted) + 1)
        # 根据新的 accepted 数量重新排序
        ranking.sort(key=lambda x: x.accepted, reverse=True)
        for i in range(len(ranking)):
            ranking[i].rank = i
        return ranking

    def fetch_user(self, uid: str) -> pixie.Image:
        logging.info(f"正在获取用户 {uid} 的信息")
        self.begin_session()
        data_source = self.config.get_config()["board_name"]
        logo_url = get_site_icon_url(self.config)

        user = fetch_user(self.config, uid)
        if user is None:
            return render_user_notice(self.config, self.config.get_config()["handler"],
                                      "用户不存在", f"未找到 UID 为 {uid} 的用户",
                                      os.path.join(self.config.work_dir, "data", "logo.png"),
                                      data_source=data_source, logo_url=logo_url)

        solved = re.search(r"解决了\s*(\d+)\s*道题目", user.progress)
        rating = re.search(r"RP[:：]\s*([\d.]+)", user.progress)
        rank = re.search(r"No\.\s*(\d+)", user.progress)

        submission_info = [submission for submission in load_json(self.config, False).submissions
                           if submission.user.uid == uid]
        total_submissions = len(submission_info)
        total_score = sum(submission.score for submission in submission_info)
        accepted_submissions = sum(1 for submission in submission_info
                                   if submission.verdict == "Accepted")
        metrics = [
            ("通过题目", solved.group(1) if solved else "-"),
            ("今日提交", str(total_submissions)),
            ("平均分数", f"{total_score / total_submissions:.2f}" if total_submissions else "-"),
            ("AC 率", (f"{accepted_submissions / total_submissions * 100:.2f}"
                       if total_submissions else "-")),
        ]

        try:
            recent_submissions = fetch_recent_submissions(self.config, uid)
        except Exception as e:
            logging.warning(f"获取用户 {uid} 的最近提交失败: {e}")
            recent_submissions = []
        recent_lines = [
            f"{submission.problem_name} · {submission.verdict} · {submission.score} 分 · "
            f"{datetime.datetime.fromtimestamp(submission.at).strftime('%y/%m/%d %H:%M')}"
            for submission in recent_submissions
        ]

        social = ([f"邮箱 {user.mail}"] if user.mail else []) + ([f"QQ {user.qq}"] if user.qq else [])
        status_text = re.sub(r"^UID:\s*", "UID ", user.status)
        timeline = [re.sub(r"[,，]\s*", " · ", status_text)] if status_text else [f"UID {uid}"]
        description = [line.strip() for line in user.description.split("\n") if line.strip()]

        sections = []
        if recent_lines:
            sections.append(UserCardSection("最近提交", recent_lines))
        if description:
            sections.append(UserCardSection("用户描述", description))

        info = UserCardInfo(
            platform_name=self.config.get_config()["handler"],
            handle=user.name,
            avatar_url=user.avatar,
            logo_url=logo_url,
            data_source=data_source,
            rating=rating.group(1) if rating else "",
            rank=f"No. {rank.group(1)}" if rank else "",
            social=social,
            timeline=timeline,
            metrics=metrics,
            sections=sections,
        )
        return UserCardGenerator(
            self.config, info, os.path.join(self.config.work_dir, "data", "logo.png")
        ).render()
