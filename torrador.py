# encoding: utf-8

import argparse
import csv
import datetime
import os
import sys
import time

import rows
import rows.utils

import machines
import settings
import utils


# TODO: we may reproduce other features than temperature (like burner on/off)
# during roasting
# TODO: must close cylinder if `roaster.automatic`, even on manual mode
# TODO: `utils.max_temp` is getting a wrong temperature
# TODO: if on `--auto` and the time for this roast is taking more than the
# setup, will get zero values and the roast may never finish
# TODO: replace prints with proper logging
# TODO: add debug logs on roaster actions


def print_stats(data, setup, turning_point_temp):
    seconds = data['roast_time']
    pretty_time = utils.pretty_seconds(seconds)
    ar = data['temp_air']
    data_hora = data['datetime']
    forno = data['temp_fire']
    grao = data['temp_bean']
    set_point = data['temp_goal']
    posicao_servo = data['servo_position']
    setup_data = setup.get(pretty_time)
    if not setup_data:
        setup_data = setup.get(utils.pretty_seconds(seconds - 1))
    if not setup_data:
        setup_data = setup.get(utils.pretty_seconds(seconds + 1))
    temperatura_setup = setup_data.temp_bean if setup_data else 0
    ar_setup = setup_data.temp_air if setup_data else 0
    posicao_setup = setup_data.servo_position if setup_data else 0
    forno_setup = setup_data.temp_fire if setup_data else 0
    print(f'{data_hora} {pretty_time} '
          f'GRAO: {grao:3d} (s: {temperatura_setup:3d}) '
          f'AR: {ar:3d} (s: {ar_setup:3d}) '
          f'FORNO: {forno:04d} (s: {forno_setup:04d}) '
          f'TP: {turning_point_temp:04d} '
          f'SV: {posicao_servo:5.2f} (s: {posicao_setup:5.2f})')


parser = argparse.ArgumentParser()
parser.add_argument('numero_torra', type=int)
parser.add_argument('minutos_totais', type=float)
parser.add_argument('setup_filename')
parser.add_argument('--auto', action='store_true')
parser.add_argument('--fake', action='store_true')
parser.add_argument('--control_type',
                    choices=['bean-temperature', 'fire-temperature',
                             'servo-position'], default='fire-temperature')
parser.add_argument('--last_bean_temperature', type=int)
args = parser.parse_args()

control_type = args.control_type
numero_torra = args.numero_torra
minutos_totais = args.minutos_totais
total_time = minutos_totais * 60
show_interval = 15
wait_interval = 1
setup_interval = 1
start_mixer_remaining_degrees = 10
setup = utils.load_setup(args.setup_filename, interval=setup_interval)
last_setup_temperature = (args.last_bean_temperature or
                          utils.max_temp(args.setup_filename))
last_setup_time = max(setup.keys())
hour, minute, second = [int(part) for part in last_setup_time.split(':')]
last_setup_seconds = hour * 3600 + minute * 60 + second


print('Conectando ao controlador... ', end='', flush=True)
if not args.fake:
    roaster = machines.CarmoMaq10(settings.ROASTER_HOST, settings.ROASTER_PORT)
else:
    roaster = machines.FakeMachine()
roaster.connect()
print('feito!')


if not roaster.cylinder:
    print('Ligando cilindro... ', end='', flush=True)
    roaster.set_cylinder(True)
    print('feito!')
else:
    print('Cilindro ligado.')


if not roaster.burner:
    print('Acendendo chama... ', end='', flush=True)
    roaster.set_burner(True)
    print('feito!')
else:
    print('Chama acesa.')


if roaster.bean_entrance:
    print('Fechando moega... ', end='', flush=True)
    roaster.close_bean_entrance()
    time.sleep(roaster.TIME_BEAN_ENTRANCE_PISTON)
    print('feito!')

if roaster.bean_exit:
    print('Fechando cilindro... ', end='', flush=True)
    roaster.close_bean_exit()
    time.sleep(roaster.TIME_BEAN_EXIT_PISTON)
    print('feito!')

if roaster.cooler_exit:
    print('Fechando saída do mexedor... ', end='', flush=True)
    roaster.close_cooler_exit()
    time.sleep(roaster.TIME_COOLER_EXIT_PISTON)
    print('feito!')

if not args.auto:
    print('Modo manual.')
    print(
        'Alterando modo de torra para manual... ',
        end='',
        flush=True,
    )
    roaster.set_mode('manual')
    print('feito!')


    # TODO: what if the hopper is not automated?
    print('Abra a moega pela interface.')
    if args.fake:
        roaster.close_bean_entrance()
    while not roaster.bean_entrance:
        time.sleep(0.05)

    print('Iniciando torra... ', end='', flush=True)
    roaster.stop_roast()
    roaster.start_roast()
    print('feito!')

else:
    print('MODO AUTOMÁTICO! Deixa comigo :)')

    if 'temperature' in control_type:
        print(
            f'Alterando PID para seguir: {control_type}... ',
            end='',
            flush=True,
        )
        roaster.set_pid_reference(control_type.split('-')[0])
        print('feito!')
    elif control_type == 'servo-position':
        print('Reprodução será através do servo motor.')

    initial = setup['00:00:00']
    roaster.set_alarm(initial.temp_bean)
    if control_type == 'bean-temperature':
        roaster.set_setpoint(initial.temp_bean)
    elif control_type == 'fire-temperature':
        roaster.set_setpoint(initial.temp_fire)
    roaster.set_servo_position(setup['00:00:00'].servo_position)
    print(f'Initial temperatures from setup - BEAN: {initial.temp_bean}, '
          f'AIR:  {initial.temp_air}, '
          f'FIRE: {initial.temp_fire}')

    roaster.set_mode('manual')
    drop_temp = initial.temp_fire
    if roaster.data['temp_fire'] <= drop_temp:
        direction = 'up'
    else:
        direction = 'down'
    while True:
        data = roaster.data
        current_temp = data['temp_fire']
        servo_position = data['servo_position']
        if current_temp == drop_temp:
            break

        elif current_temp < drop_temp:
            if direction == 'down':
                break

            if roaster.bean_exit:
                try:
                    roaster.close_bean_exit()
                except:
                    print('ERRO: feche o cilindro')
            servo_position += 3
            if servo_position < 10:
                servo_position = 10
            elif servo_position > 25:
                servo_position = 25
            roaster.set_burner(True)
            roaster.set_servo_position(servo_position)

        elif current_temp >= drop_temp:
            if direction == 'up':
                break

            roaster.set_burner(False)

        time.sleep(0.1)

    if roaster.bean_exit:
        roaster.close_bean_exit()
        time.sleep(roaster.TIME_BEAN_ENTRANCE_PISTON)
    roaster.set_burner(True)
    roaster.open_bean_entrance()  # found it! o/

    if control_type == 'servo-position':
        print(
            'Alterando modo de torra para manual (não receita)... ',
            end='',
            flush=True,
        )
        roaster.set_mode('manual')
        print('feito!')
    else:
        print(
            'Alterando modo de torra para receita... ',
            end='',
            flush=True,
        )
        roaster.set_mode('recipe')
        print('feito!')

    print('Iniciando torra... ', end='', flush=True)
    roaster.restart_roast()
    roaster.set_alarm(last_setup_temperature)
    print('feito!')
    print(f'Temperatura final: {last_setup_temperature}')


csv_filename = str(settings.DATA_PATH / f'torra-{numero_torra}.csv')
xls_filename = str(settings.DATA_PATH / f'torra-{numero_torra}.xls')
with open(csv_filename, mode='w', encoding='utf8') as fobj:
    writer = None
    finished = False
    passed_turning_point = False
    turning_point_temp = 0
    opened_bean_exit = 99999999
    last_bean_temperature = 999999999
    start_time = time.time()

    try:
        while not finished:
            start_loop = time.time()

            data = roaster.data
            data['datetime'] = utils.pretty_now()
            if writer is None:
                writer = csv.DictWriter(
                    fobj,
                    fieldnames=list(data.keys()),
                )
                writer.writeheader()
            writer.writerow(data)

            seconds = int(data['roast_time'])

            if roaster.automatic and seconds > 30 and roaster.bean_entrance:
                try:
                    roaster.close_bean_entrance()
                except:
                    print('Error trying to close bean entrance.')

            current_bean_temperature = int(data['temp_bean'])
            if not passed_turning_point and seconds > 10 and \
                    last_bean_temperature < current_bean_temperature:
                passed_turning_point = True
                turning_point_temp = current_bean_temperature

            if args.auto:
                # Set next temperature goal
                next_time = utils.pretty_seconds(seconds + 1)
                row = setup.get(next_time)
                if row:
                    if control_type == 'servo-position':
                        roaster.set_mode('manual')
                        roaster.set_servo_position(row.servo_position)

                    elif control_type == 'bean-temperature':
                        if passed_turning_point:
                            roaster.set_mode('recipe')
                            roaster.set_pid_reference(control_type.split('-')[0])
                            roaster.set_setpoint(row.temp_bean)

                    elif control_type == 'fire-temperature':
                        roaster.set_mode('recipe')
                        roaster.set_pid_reference(control_type.split('-')[0])
                        roaster.set_setpoint(row.temp_fire)

                if passed_turning_point:
                    delta_temperature = last_setup_temperature - current_bean_temperature

                    # Automatically start mixer when finishing roast
                    if delta_temperature <= start_mixer_remaining_degrees:
                        roaster.set_alarm(current_bean_temperature)
                        if not roaster.mixer:
                            roaster.set_mixer(True)
                        if not roaster.cooler:
                            roaster.set_cooler(True)
                        if roaster.cooler_exit:
                            try:
                                roaster.close_cooler_exit()
                            except:
                                print('FECHE A SAÍDA DO MEXEDOR!')

                    # Automatically open bean exit if final temperature is met
                    if last_setup_temperature <= current_bean_temperature:
                        roaster.set_alarm(current_bean_temperature)
                        if not roaster.bean_exit:
                            roaster.set_burner(False)
                            try:
                                roaster.open_bean_exit()
                                opened_bean_exit = seconds
                            except:
                                print('ABRA O TAMBOR!')

                    # Automatically close bean exit after openning it
                    if seconds - opened_bean_exit >= 30:
                        if roaster.bean_exit:
                            try:
                                roaster.close_bean_exit()
                            except:
                                print('FECHE O TAMBOR!')

            last_bean_temperature = current_bean_temperature

            if seconds % show_interval == 0:
                print_stats(data, setup, turning_point_temp)

            finished = time.time() - start_time > total_time
            while time.time() - start_loop <= wait_interval:
                time.sleep(0.05)

    except KeyboardInterrupt:
        pass

print(
    'Finalizada a gravação. Fechando conexão e convertendo arquivo... ',
    end='',
    flush=True,
)
roaster.close()
table = rows.import_from_csv(csv_filename)
rows.export_to_xls(table, xls_filename)
print(' feito!')
