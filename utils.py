import datetime

import rows.utils


def load_setup(filename, interval=15):
    data = rows.utils.import_from_uri(filename, default_encoding='utf8')

    setup = {}
    started = False
    for row in data:
        if row.roast_time == 0:
            started = True
        if not started:
            continue

        if row.roast_time % interval == 0:
            setup[pretty_seconds(row.roast_time)] = row

    return setup


def pretty_seconds(seconds):
    pretty = str(datetime.timedelta(seconds=seconds))
    if len(pretty) == 7:  # missing a '0' to be fixed length
        pretty = '0' + pretty

    return pretty


def pretty_now():
    return str(datetime.datetime.now()).split('.')[0].replace(' ', 'T')
