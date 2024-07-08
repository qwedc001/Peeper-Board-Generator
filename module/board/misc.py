import logging
import sys

from module.ImgConvert import StyledString
from module.config import Config
from module.structures import SubmissionData
from module.submission import rank_by_verdict, get_first_ac, classify_by_verdict, get_hourly_submissions, \
    get_most_popular_problem, count_users_submitted
from module.utils import load_json, get_date_string


class MiscBoard:

    def __init__(self, play_of_the_oj: str, top_five: list[dict], total_board: list[dict], total_submits: int,
                 first_ac: SubmissionData, verdict_data: dict, avg_score: float, ac_rate: float, hourly_data: dict,
                 popular_problem: tuple[str, int], users_submitted: int):
        self.play_of_the_oj = play_of_the_oj
        self.top_five = top_five
        self.total_board = total_board
        self.total_submits = total_submits
        self.first_ac = first_ac
        self.verdict_data = verdict_data
        self.avg_score = avg_score
        self.ac_rate = ac_rate
        self.hourly_data = hourly_data
        self.popular_problem = popular_problem
        self.users_submitted = users_submitted


def generate_board_data(submissions: list[SubmissionData]) -> MiscBoard:
    result = {}
    accepted_desc = rank_by_verdict(submissions)['Accepted']
    result['play_of_the_oj'] = max(accepted_desc, key=accepted_desc.get)  # 昨日
    total_board = []
    rank = 1
    for i, (user, ac) in enumerate(accepted_desc.items()):
        if i > 0 and ac != accepted_desc[list(accepted_desc.keys())[i - 1]]:
            rank = i + 1
        total_board.append({"user": user, "ac": ac, "rank": rank})
    result['top_five'] = total_board[:5]  # 昨日
    result['total_board'] = total_board  # 昨日 / 今日
    result['total_submits'] = len(submissions)  # 昨日 / 今日
    result['first_ac'] = get_first_ac(submissions)  # 昨日 / 今日
    result['verdict_data'] = classify_by_verdict(submissions)  # 昨日 / 今日
    result['avg_score'] = result['verdict_data']['avg_score']  # 昨日 / 今日
    result['ac_rate'] = result['verdict_data']['ac_rate']  # 昨日 / 今日
    result['hourly_data'] = get_hourly_submissions(submissions)  # 昨日 / 今日
    result['popular_problem'] = get_most_popular_problem(submissions)  # 昨日 / 今日
    result['users_submitted'] = count_users_submitted(submissions)  # 昨日 / 今日
    board = MiscBoard(play_of_the_oj=result['play_of_the_oj'], top_five=result['top_five'],
                      total_board=result['total_board'], total_submits=result['total_submits'],
                      first_ac=result['first_ac'], verdict_data=result['verdict_data'], avg_score=result['avg_score'],
                      ac_rate=result['ac_rate'], hourly_data=result['hourly_data'],
                      popular_problem=result['popular_problem'],
                      users_submitted=result['users_submitted'])
    return board


class MiscBoardGenerator:

    @staticmethod
    def generate_image(config: Config, board_type: str, verdict: str = "Accepted"):
        today = load_json(config, False)
        if board_type == "full":
            title = StyledString("昨日卷王天梯榜", 'H', 96)
            subtitle = StyledString(f'{get_date_string(True)} {config.get_config("oj_name")} Rank List', 'H', 36)

            try:
                yesterday = load_json(config, True)
            except FileNotFoundError:
                logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
                sys.exit(1)
            data = generate_board_data(yesterday.submissions)
            rank = today.rankings
            # 对于 full 榜单的图形逻辑

            play_of_the_oj_title = StyledString(f"昨日卷王", 'B', 36)
            play_of_the_oj = StyledString(data.play_of_the_oj, 'H', 72)

            top_5_subtitle = StyledString("过题数榜单", "B", 36)
            top_5_title = StyledString("昨日过题数", "H", 72)
            top_5_mark = StyledString("Top 5th", "H", 48)

            top_5_detail = []


        if board_type == "now":
            if verdict == "Accepted":
                title = StyledString("今日当前提交榜", 'H', 96)
                subtitle = StyledString(f'{get_date_string(True)} {config.get_config("oj_name")} Rank List', 'H', 36)

                data = generate_board_data(today.submissions)
                rank = today.rankings[:5]
                # 对于 now 榜单的图形逻辑
            else:
                title = StyledString(f"今日当前{verdict}榜", 'H', 96)
                subtitle = StyledString(f'{get_date_string(True)} {config.get_config("oj_name")} Rank List', 'H', 36)
                data = generate_board_data([s for s in today.submissions if s.verdict == verdict])
                rank = rank_by_verdict([s for s in today.submissions if s.verdict == verdict])
                # 对于分 verdict 的 now 榜单的图形逻辑
