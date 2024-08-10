import json
import os


class Configs:
    def __init__(self, work_dir: str, configs_path: str = 'config.json'):
        self.work_dir = work_dir
        json_path = os.path.join(self.work_dir, configs_path)
        config_file = open(json_path, 'r', encoding='utf-8')
        self.json_configs = json.loads(config_file.read())
        self.configs = []
        for config in self.json_configs:
            self.configs.append(Config(self.work_dir, config))


class Config:
    def __init__(self, work_dir: str, json_cfg: dict):
        self.work_dir = work_dir
        self.jsonCfg = json_cfg
        if not self.jsonCfg['url'].endswith('/'):
            self.jsonCfg['url'] = self.jsonCfg['url'] + '/'

    def get_config(self):
        return self.jsonCfg

    def set_config(self, key, value):
        self.jsonCfg[key] = value

    @classmethod
    def from_json(cls, config):
        pass
