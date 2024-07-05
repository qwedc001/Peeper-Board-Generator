import logging
from module.config import Config
import argparse

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("程序开始工作")
    parser = argparse.ArgumentParser(description='Hydro Bot Args Parser')
    parser.add_argument('--full', action="store_true", help='生成今日榜单')
    parser.add_argument('--now', action="store_true", help='生成从今日0点到当前时间的榜单')
    parser.add_argument('--version', action="store_true", help='版本号信息')
    parser.add_argument('--verdict', action="store_true", help='指定榜单对应verdict')
    parser.add_argument('--help', action="store_true", help='帮助信息')
    args = parser.parse_args()
    if args.full:
        logging.info("Generating full ranklist")
    elif args.now:
        logging.info("Generating ranklist from 0:00 to now")