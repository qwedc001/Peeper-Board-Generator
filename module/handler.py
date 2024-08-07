from requests import Session


class BasicHandler:

    def __init__(self, name):
        self.name = name

    def save_daily(self, mode: str):
        pass

    def login(self, credentials) -> Session:
        pass

    def fetch_user(self, uid):
        pass
