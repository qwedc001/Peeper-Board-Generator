import json
import os


class Config:
    def __init__(self, config_path: str = 'config.json'):
        self.work_dir = os.path.abspath(os.path.curdir)
        json_path = os.path.join(self.work_dir, config_path)
        config_file = open(json_path, 'r', encoding='utf-8')
        self.jsonCfg = json.loads(config_file.read())
        config_file.close()

    def get_config(self, key):
        return self.jsonCfg[key]

    def set_config(self, key, value):
        self.jsonCfg[key] = value

    def get_work_path(self):
        return self.work_dir
