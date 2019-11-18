import datetime

import rows.utils


def load_setup(filename, interval=15):
    data = rows.utils.import_from_uri(filename, default_encoding='utf8')

    setup = {}
    started = False
    for row in data:
        if not any(row._asdict().values()):
            continue
        if row.roast_time == 0:
            started = True
        if not started:
            continue
        if row.roast_time % interval == 0:
            setup[pretty_seconds(row.roast_time)] = row

    return setup


def max_temp(filename):
    data = rows.utils.import_from_uri(filename, default_encoding='utf8')

    last_temp = 9999999999
    turning_point = False  # reversed turning point
    for row in reversed(data):
        if not any(row._asdict().values()):
            continue
        temp = row.temp_bean
        if not turning_point and temp > last_temp and row.roast_time > 30:
            turning_point = True
        elif turning_point and temp < last_temp:
            return last_temp

        last_temp = temp


def pretty_seconds(seconds):
    pretty = str(datetime.timedelta(seconds=seconds))
    if len(pretty) == 7:  # missing a '0' to be fixed length
        pretty = '0' + pretty

    return pretty


def pretty_now():
    return str(datetime.datetime.now()).split('.')[0].replace(' ', 'T')


def get_last_setup_for(setup, seconds, variable):
    found = False
    while not found:
        next_time = pretty_seconds(seconds)
        row = setup.get(next_time)
        if row:
            # TODO: if roast is not finished, calculate a proper temp
            value = getattr(row, variable)
            if value is not None:
                found = True
                break
        seconds -= 1
    return row
