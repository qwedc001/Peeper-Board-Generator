import json
import os


class Config:
    def __init__(self, work_dir: str, config_path: str = 'config.json'):
        self.work_dir = work_dir
        json_path = os.path.join(self.work_dir, config_path)
        config_file = open(json_path, 'r', encoding='utf-8')
        self.jsonCfg = json.loads(config_file.read())
        if not self.jsonCfg['url'].endswith('/'):
            self.jsonCfg['url'] = self.jsonCfg['url'] + '/'
        config_file.close()

    def get_config(self):
        return self.jsonCfg

    def set_config(self, key, value):
        self.jsonCfg[key] = value
