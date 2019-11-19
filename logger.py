import datetime
import json

from redis import Redis

import utils


class Logger:

    def __init__(self, redis_host=None, redis_port=None, redis_db=None, redis_channel=None):
        if any((redis_host, redis_port, redis_db)):
            self.redis = Redis(redis_host, redis_port, db=redis_db)
            self.redis_channel = redis_channel
        else:
            self.redis = None

    def log(self, content, message_type="text"):
        timestamp = datetime.datetime.now().isoformat().split(".")[0]
        if self.redis:
            data = {
                "message_type": message_type,
                "timestamp": timestamp,
            }
            if isinstance(content, dict):
                data.update(content)
            else:
                data["message"] = str(content)
            self.redis.publish(self.redis_channel, json.dumps(data))

        if message_type == "text":
            print(f"[{timestamp}] {content}")

    def log_stats(self, data, setup, turning_point_temp):
        seconds = data["roast_time"]
        pretty_time = utils.pretty_seconds(seconds)
        ar = data["temp_air"]
        forno = data["temp_fire"]
        grao = data["temp_bean"]
        set_point = data["temp_goal"]
        posicao_servo = data["servo_position"]
        setup_data = setup.get(pretty_time)
        if not setup_data:
            setup_data = setup.get(utils.pretty_seconds(seconds - 1))
        if not setup_data:
            setup_data = setup.get(utils.pretty_seconds(seconds + 1))
        temperatura_setup = setup_data.temp_bean if setup_data else 0
        ar_setup = setup_data.temp_air if setup_data else 0
        posicao_setup = setup_data.servo_position if setup_data else 0
        forno_setup = setup_data.temp_fire if setup_data else 0
        self.log(
            f"{pretty_time} "
            f"GRAO: {grao:3d} (s: {temperatura_setup:3d}) "
            f"AR: {ar:3d} (s: {ar_setup:3d}) "
            f"FORNO: {forno:04d} (s: {forno_setup:04d}) "
            f"TP: {turning_point_temp:04d} "
            f"SV: {posicao_servo:5.2f} (s: {posicao_setup:5.2f})"
        )
