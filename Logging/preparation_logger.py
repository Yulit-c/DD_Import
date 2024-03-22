import json
from pathlib import Path
from logging import getLogger, config

path_log_config = Path(__file__).parent.joinpath(r'log_config.json')
with open(path_log_config, 'r') as f:
    log_conf = json.load(f)
config.dictConfig(log_conf)

def preparating_logger(name: str):
    return getLogger(name)