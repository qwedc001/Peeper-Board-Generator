import logging
import os
import traceback

from module.config import Config
from module.Hydro.entry import HydroHandler
from module.board.misc import MiscBoardGenerator
import argparse

from module.utils import search_user_by_uid, fuzzy_search_user
from module.verdict import ALIAS_MAP
import sys

config = Config()
url = config.get_config("url")
VERSION_INFO = "v1.2.0"


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
        parser = DefaultHelpParser(description='Peeper-Board-Generator OJ榜单图片生成器')
        required_para = parser.add_mutually_exclusive_group(required=True)
        required_para.add_argument('--version', action="store_true", help='版本号信息')
        required_para.add_argument('--full', action="store_true", help='生成昨日榜单')
        required_para.add_argument('--now', action="store_true", help='生成从今日0点到当前时间的榜单')
        required_para.add_argument('--query_uid', type=str, help='根据 uid 查询指定用户的信息')
        required_para.add_argument('--query_name', type=str, help='根据用户名查询指定用户的信息')
        parser.add_argument('--output', type=str, help='指定生成图片的路径 (包含文件名)')
        parser.add_argument('--verdict', type=str, help='指定榜单对应verdict (使用简写)')
        args = parser.parse_args()
        if not args.verdict:
            args.verdict = ALIAS_MAP["AC"]
        else:
            args.verdict = ALIAS_MAP[args.verdict]
        if not args.output:
            args.output = os.path.join(config.work_dir, config.get_config('data'), "output.png") if args.full or args.now else os.path.join(config.work_dir, config.get_config('data'), "output.txt")
        handler = HydroHandler(config, url)
        if args.version:
            print(f"Peeper-Board-Generator {VERSION_INFO}")
            sys.exit(0)
        if args.full:
            logging.info("正在生成昨日榜单")
            handler.save_daily("full")
            output_img = MiscBoardGenerator.generate_image(config, "full",
                                                           os.path.join(config.work_dir, config.get_config('data'),
                                                                        f'logo.png'))
            output_img.write_file(args.output)
            logging.info(f"生成图片成功，路径为{args.output}")
        elif args.now:
            logging.info("正在生成0点到现在时间的榜单")
            handler.save_daily("now")
            output_img = MiscBoardGenerator.generate_image(config, "now",
                                                           os.path.join(config.work_dir, config.get_config('data'),
                                                                        f'logo.png'), verdict=args.verdict)
            output_img.write_file(args.output)
            logging.info(f"生成图片成功，路径为{args.output}")
        elif args.query_uid:
            logging.info("正在查询指定用户信息")
            result = search_user_by_uid(config, args.query_uid, handler)
            with open(args.output, "w",encoding='utf-8') as f:
                f.write(result)
        elif args.query_name:
            logging.info("正在查询指定用户信息")
            result = fuzzy_search_user(config, args.query_name, handler)
            with open(args.output, "w",encoding='utf-8') as f:
                f.write(result)
        else:
            parser.print_help()
            sys.exit(0)

        with open(os.path.join(os.path.dirname(__file__), "last_traceback.log"), "w") as f:
            f.write("ok")
    except Exception as e:
        logging.error(e, exc_info=True)
        with open(os.path.join(os.path.dirname(__file__), "last_traceback.log"), "w") as f:
            traceback.print_exc(file=f)
