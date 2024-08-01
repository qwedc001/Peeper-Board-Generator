import logging
import os
import traceback

from module.config import Config
from module.Hydro.entry import HydroHandler
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
    try:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        file_handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), "info.log"))
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        logging.debug("程序开始工作")
        parser = DefaultHelpParser(description='Hydro Bot Args Parser')
        required_para = parser.add_mutually_exclusive_group(required=True)
        required_para.add_argument('--full', action="store_true", help='生成今日榜单')
        required_para.add_argument('--now', action="store_true", help='生成从今日0点到当前时间的榜单')
        parser.add_argument('--version', action="store_true", help='版本号信息')
        parser.add_argument('--verdict', type=str, help='指定榜单对应verdict (使用简写)')
        parser.add_argument('--output', type=str, help='指定生成图片的路径 (包含文件名)', required=True)
        args = parser.parse_args()
        if not args.verdict:
            args.verdict = ALIAS_MAP["AC"]
        else:
            args.verdict = ALIAS_MAP[args.verdict]
        handler = HydroHandler(config, url)
        handler.save_daily()
        if args.full:
            logging.info("正在生成昨日榜单")
            output_img = MiscBoardGenerator.generate_image(config, "full",
                                                           os.path.join(config.work_dir, config.get_config('data'),
                                                                        f'logo.png'))
            output_img.write_file(args.output)
        elif args.now:
            logging.info("正在生成0点到现在时间的榜单")
            output_img = MiscBoardGenerator.generate_image(config, "now",
                                                           os.path.join(config.work_dir, config.get_config('data'),
                                                                        f'logo.png'), verdict=args.verdict)
            output_img.write_file(args.output)
        else:
            parser.print_help()
            sys.exit(0)

        with open(os.path.join(os.path.dirname(__file__), "last_traceback.log"), "w") as f:
            f.write("ok")
    except Exception as e:
        logging.error(e, exc_info=True)
        with open(os.path.join(os.path.dirname(__file__), "last_traceback.log"), "w") as f:
            traceback.print_exc(file=f)
