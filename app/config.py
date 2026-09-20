import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def data_dir() -> Path:
    return Path(os.environ.get('TALK_ASSISTANT_DATA_DIR') or (Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'TalkAssistant'))


DEFAULTS = {'name': '', 'duration': 95, 'remember_path': False, 'last_path': ''}


def load_config() -> dict:
    try:
        value = json.loads((data_dir() / 'config.json').read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            return DEFAULTS.copy()
        return {
            'name': value.get('name') if isinstance(value.get('name'), str) and value['name'].strip() else '',
            'duration': value.get('duration') if type(value.get('duration')) is int and 1 <= value['duration'] <= 1440 else 95,
            'remember_path': value.get('remember_path') if type(value.get('remember_path')) is bool else False,
            'last_path': value.get('last_path') if isinstance(value.get('last_path'), str) and value.get('remember_path', False) else '',
        }
    except (OSError, ValueError):
        return DEFAULTS.copy()


def save_config(value: dict):
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'config.json'
    temp = directory / 'config.tmp'
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def setup_logging():
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / 'app.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger = logging.getLogger('app')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info('程序启动')
