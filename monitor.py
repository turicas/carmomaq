import json

from flask import Flask, jsonify, render_template
from redis import Redis

import settings


app = Flask(__name__)
redis = Redis(settings.REDIS_HOST, settings.REDIS_PORT, db=settings.REDIS_DB)
pubsub = redis.pubsub()
pubsub.subscribe(settings.REDIS_CHANNEL)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/message")
def message():
    messages, finished, max_messages = [], False, 30
    while not finished:
        content = pubsub.get_message()
        finished = content is None
        if not finished:
            data = content["data"]
            if isinstance(data, bytes):
                messages.append({
                    "channel": content["channel"].decode("utf-8"),
                    "data": json.loads(data),
                })
        if len(messages) >= max_messages:
            finished = True

    return jsonify(messages)


if __name__ == "__main__":
    app.run()
