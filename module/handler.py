import requests


class BasicHandler:

    def __init__(self, name: str):
        self.name = name

    # 保存 DailyJson 的数据到本地
    def save_daily(self, mode: str):
        pass

    # 登录到特定网站的接口, 如果登录成功返回一个 Session 对象
    # 非必须，有些网站获取数据使用的是 API
    def login(self, credentials) -> requests.Session:
        pass

    def fetch_user(self, uid):
        pass
