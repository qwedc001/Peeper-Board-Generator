import logging
import os

from module.config import Config
from module.hydro.entry import HydroHandler
from module.board.misc import MiscBoardGenerator
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
        MiscBoardGenerator.generate_image(config,"full", os.path.join(config.work_dir, config.get_config('data'), f'logo.png'))
    elif args.now:
        logging.info("正在生成0点到现在时间的榜单")
        MiscBoardGenerator.generate_image(config,"now", os.path.join(config.work_dir, config.get_config('data'), f'logo.png'), verdict=args.verdict)
    else:
        parser.print_help()
        sys.exit(0)
