import logging
import os
import traceback

from module.Hydro.entry import HydroHandler
from module.config import Configs, Config
from module.board.misc import MiscBoardGenerator
import argparse

from module.constants import VERSION_INFO
from module.utils import search_user_by_uid, fuzzy_search_user
from module.verdict import ALIAS_MAP
import sys

sub_handlers = {
    'Hydro': HydroHandler,
    "Codeforces": "TODO"  # TODO: 1.3版本支持
}

work_dir = os.path.dirname(__file__)


class DefaultHelpParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %sn' % message)
        self.print_help()
        sys.exit(2)


def generate(cur_config: Config, multi: bool = False, separate_cols: bool = False):
    logging.info(f"正在生成 {cur_config.get_config()['board_name']} 榜单")
    if not args.output or multi:
        args.output = os.path.join(work_dir, "data",
                                   f'{cur_config.get_config()["id"]}-output.png') \
            if args.full or args.now else os.path.join(work_dir, "data",
                                                       f'{cur_config.get_config()["id"]}-output.txt')
    handler = sub_handlers.get(cur_config.get_config()['handler'])(cur_config)
    if args.full:
        logging.info("正在生成昨日榜单")
        handler.save_daily("full")
        output_img = MiscBoardGenerator.generate_image(cur_config, "full",
                                                       os.path.join(work_dir, "data", f'logo.png'),
                                                       separate_columns=separate_cols)
        output_img.write_file(args.output)
        logging.info(f"生成图片成功，路径为{args.output}")
    elif args.now:
        logging.info("正在生成0点到现在时间的榜单")
        handler.save_daily("now")
        output_img = MiscBoardGenerator.generate_image(cur_config, "now",
                                                       os.path.join(work_dir, "data", f'logo.png'),
                                                       verdict=args.verdict,
                                                       separate_columns=separate_cols)
        output_img.write_file(args.output)
        logging.info(f"生成图片成功，路径为{args.output}")
    elif args.query_uid:
        logging.info("正在查询指定用户信息")
        result = search_user_by_uid(args.query_uid, handler)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(result)
    elif args.query_name:
        logging.info("正在查询指定用户信息")
        result = fuzzy_search_user(cur_config, args.query_name, handler)
        with open(args.output, "w", encoding='utf-8') as f:
            f.write(result)


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    file_handler = logging.FileHandler(os.path.join(work_dir, "info.log"), encoding='utf-8')
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    parser = DefaultHelpParser(description='Peeper-Board-Generator OJ榜单图片生成器')
    required_para = parser.add_mutually_exclusive_group(required=True)
    required_para.add_argument('--version', action="store_true", help='版本号信息')
    required_para.add_argument('--full', action="store_true", help='生成昨日榜单')
    required_para.add_argument('--now', action="store_true", help='生成从今日0点到当前时间的榜单')
    required_para.add_argument('--query_uid', type=str, help='根据 uid 查询指定用户的信息')
    required_para.add_argument('--query_name', type=str, help='根据用户名查询指定用户的信息')
    parser.add_argument('--output', type=str, help='指定生成图片的路径 (包含文件名)')
    parser.add_argument('--verdict', type=str, help='指定榜单对应verdict (使用简写)')
    parser.add_argument('--id', type=str, help='生成指定 id 的榜单(留空则生成全部榜单)')
    parser.add_argument('--separate_cols', action='store_true', help='是否启用分栏特性')
    parser.add_argument('--performance_statistics', action='store_true', help='性能测试')
    parser.add_argument('--config', type=str, help='指定配置文件路径', default=os.path.join(os.path.dirname(__file__), "config.json"))

    statistics_file = open(os.path.join(work_dir, "performance.log"), 'w', encoding='utf-8')
    try:
        args = parser.parse_args()

        # 从指定路径加载配置
        configs = Configs(args.config).get_configs()

        if not args.performance_statistics:
            statistics_file.close()
        if args.version:
            print(f"Peeper-Board-Generator {VERSION_INFO}")
            with open(args.output, "w", encoding='utf-8') as f:
                f.write(f"Peeper-Board-Generator {VERSION_INFO}")
            sys.exit(0)
        if not args.verdict:
            args.verdict = ALIAS_MAP["AC"]
        else:
            args.verdict = ALIAS_MAP[args.verdict]
        if not args.id:
            # 生成全部榜单
            for config in configs:
                config.set_config('statistic_file', statistics_file)
                generate(config, multi=True, separate_cols=args.separate_cols)
        else:
            # 生成指定 id 的榜单
            for config in configs:
                if config.get_config()['id'] == args.id:
                    config.set_config('statistic_file', statistics_file)
                    generate(config, separate_cols=args.separate_cols)
                    break
        with open(os.path.join(work_dir, "last_traceback.log"), "w", encoding='utf-8') as f:
            f.write("ok")
    except Exception as e:
        logging.error(e, exc_info=True)
        with open(os.path.join(work_dir, "last_traceback.log"), "w", encoding='utf-8') as f:
            traceback.print_exc(file=f)
    finally:
        if statistics_file:
            statistics_file.close()