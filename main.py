import logging
from module.config import Config
from module.structures import SubmissionData
from module.utils import load_json
from module.submission import rank_by_verdict, get_first_ac, classify_by_verdict, get_hourly_submissions, \
    get_most_popular_problem, count_users_submitted
from module.hydro.entry import HydroHandler
import argparse
from module.verdict import ALIAS_MAP
import sys

config = Config()
url = config.get_config("url")


class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %sn' % message)
        self.print_help()
        sys.exit(2)


def generate_full():
    today = load_json(config, False)
    try:
        yesterday = load_json(config, True)
    except FileNotFoundError:
        logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
        sys.exit(1)
    data = generate_board_data(yesterday.submissions)
    # 因为时间已经过 0 点 所以此处需要的 rank 实际来源于today 的 ranking 表
    rank = today.rankings


def generate_now(verdict):
    today = load_json(config, False)
    if verdict == "Accepted":
        data = generate_board_data(today.submissions)
        rank = today.rankings[:5]
    else:
        data = generate_board_data([s for s in today.submissions if s.verdict == verdict])
        rank = rank_by_verdict([s for s in today.submissions if s.verdict == verdict])


def generate_board_data(submissions: list[SubmissionData]) -> dict:
    result = {}
    accepted_desc = rank_by_verdict(submissions)['Accepted']
    result['play_of_the_oj'] = max(accepted_desc, key=accepted_desc.get)  # 昨日
    total_board = []
    for i, (user, ac) in enumerate(accepted_desc.items()):
        total_board.append({"user": user, "ac": ac})
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
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug("程序开始工作")
    parser = DefaultHelpParser(description='Hydro Bot Args Parser')
    required_para = parser.add_mutually_exclusive_group(required=True)
    required_para.add_argument('--full', action="store_true", help='生成今日榜单')
    required_para.add_argument('--now', action="store_true", help='生成从今日0点到当前时间的榜单')
    parser.add_argument('--version', action="store_true", help='版本号信息')
    parser.add_argument('--verdict', type=str, help='指定榜单对应verdict (使用简写)')
    args = parser.parse_args()
    if not args.verdict:
        args.verdict = ALIAS_MAP["AC"]
    else:
        args.verdict = ALIAS_MAP[args.verdict]
    handler = HydroHandler(config, url)
    handler.save_daily()
    if args.full:
        logging.info("正在生成昨日榜单")
        generate_full()
    elif args.now:
        logging.info("正在生成0点到现在时间的榜单")
        generate_now(args.verdict)
    else:
        parser.print_help()
        sys.exit(0)
