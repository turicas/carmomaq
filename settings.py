# encoding: utf-8
import pathlib


DATA_PATH = pathlib.Path("./data")
if not DATA_PATH.exists():
    DATA_PATH.mkdir()

ROASTER_HOST = "192.168.0.10"
ROASTER_PORT = 502

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_CHANNEL = "carmomaq10"
