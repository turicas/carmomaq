# encoding: utf-8

import argparse
import csv
import datetime
import os
import sys
import time

import rows
import rows.utils

import controllers
import machines
import settings
import utils
from logger import Logger

# TODO: we may reproduce other features than temperature (like burner on/off)
# during roasting
# TODO: must close cylinder if `roaster.automatic`, even on manual mode
# TODO: `utils.max_temp` is getting a wrong temperature
# TODO: if on `--auto` and the time for this roast is taking more than the
# setup, will get zero values and the roast may never finish
# TODO: add debug logs on roaster actions


def roast(args, logger):
    control_type = args.control_type
    numero_torra = args.numero_torra
    minutos_totais = args.minutos_totais
    total_time = minutos_totais * 60
    show_interval = 15
    wait_interval = 1
    setup_interval = 1
    start_mixer_remaining_degrees = 5
    setup = utils.load_setup(args.setup_filename, interval=setup_interval)
    last_setup_temperature = args.last_bean_temperature or utils.max_temp(
        args.setup_filename
    )
    last_setup_time = max(setup.keys())
    hour, minute, second = [int(part) for part in last_setup_time.split(":")]
    last_setup_seconds = hour * 3600 + minute * 60 + second


    logger.log("Conectando ao controlador... ")
    if not args.fake:
        roaster = machines.CarmoMaq10(settings.ROASTER_HOST, settings.ROASTER_PORT)
    else:
        roaster = machines.FakeMachine()
    roaster.connect()
    logger.log("  Conectado ao controlador!")


    if not roaster.cylinder:
        logger.log("Ligando cilindro... ")
        roaster.set_cylinder(True)
        logger.log("  cilindro ligado!")
    else:
        logger.log("Cilindro já ligado.")


    if not roaster.burner:
        logger.log("Acendendo chama... ")
        roaster.set_burner(True)
        logger.log("  Chama acesa!")
    else:
        logger.log("Chama já acesa.")


    if roaster.bean_entrance:
        logger.log("Fechando moega... ")
        roaster.close_bean_entrance()
        time.sleep(roaster.TIME_BEAN_ENTRANCE_PISTON)
        logger.log("  Moega fechada!")

    if roaster.bean_exit:
        logger.log("Fechando cilindro... ")
        roaster.close_bean_exit()
        time.sleep(roaster.TIME_BEAN_EXIT_PISTON)
        logger.log("  Cilindro fechado!")

    if roaster.cooler_exit:
        logger.log("Fechando saída do mexedor... ")
        roaster.close_cooler_exit()
        time.sleep(roaster.TIME_COOLER_EXIT_PISTON)
        logger.log("  Saída do mexedor fechada!")

    if not args.auto:
        logger.log("TORRANDO NO MODO MANUAL")
        logger.log("Alterando torrador para manual...")
        roaster.set_mode("manual")
        logger.log("  Torrador no manual!")

        # TODO: what if the hopper is not automated?
        logger.log("Abra a moega pela interface touch screen.")
        if args.fake:
            roaster.close_bean_entrance()
        while not roaster.bean_entrance:
            time.sleep(0.05)

        logger.log("Iniciando torra... ")
        roaster.stop_roast()
        roaster.start_roast()
        logger.log("  Torra iniciada!")

    else:
        logger.log("TORRANDO NO MODO AUTOMÁTICO! Pode ir tomar um café :)")
        controller = controllers.get_controller(control_type)(roaster, setup, logger)
        controller.before_start()

        initial = setup["00:00:00"]
        logger.log(
            f"Temperaturas iniciais do setup - GRÃO: {initial.temp_bean}, "
            f"AR:  {initial.temp_air}, "
            f"FOGO: {initial.temp_fire}"
        )
        logger.log("Ajustando temperaturas para iniciar...")

        roaster.set_mode("manual")
        drop_temp = initial.temp_fire
        if roaster.data["temp_fire"] <= drop_temp:
            direction = "up"
        else:
            direction = "down"
        while True:
            data = roaster.data
            current_temp = data["temp_fire"]
            servo_position = data["servo_position"]
            if current_temp == drop_temp:
                break

            elif current_temp < drop_temp:
                if direction == "down":
                    break

                if roaster.bean_exit:
                    try:
                        roaster.close_bean_exit()
                    except:
                        logger.log("ERRO: feche o cilindro")
                servo_position += 3
                if servo_position < 10:
                    servo_position = 10
                elif servo_position > 25:
                    servo_position = 25
                roaster.set_burner(True)
                roaster.set_servo_position(servo_position)

            elif current_temp >= drop_temp:
                if direction == "up":
                    break

                roaster.set_burner(False)

            time.sleep(0.1)

        if roaster.bean_exit:
            roaster.close_bean_exit()
            time.sleep(roaster.TIME_BEAN_ENTRANCE_PISTON)
        roaster.set_burner(True)
        roaster.open_bean_entrance()  # found it! o/

        controller.after_start()

        logger.log("Iniciando torra... ")
        roaster.restart_roast()
        roaster.set_alarm(last_setup_temperature)
        logger.log("  Torra iniciada!")
        logger.log(f"Temperatura final: {last_setup_temperature}")

    csv_filename = str(settings.DATA_PATH / f"torra-{numero_torra}.csv")
    xls_filename = str(settings.DATA_PATH / f"torra-{numero_torra}.xls")
    with open(csv_filename, mode="w", encoding="utf8") as fobj:
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
                data["datetime"] = utils.pretty_now()
                if writer is None:
                    writer = csv.DictWriter(fobj, fieldnames=list(data.keys()),)
                    writer.writeheader()
                writer.writerow(data)
                logger.log(data, message_type="data")

                seconds = int(data["roast_time"])

                if roaster.automatic and seconds > 30 and roaster.bean_entrance:
                    try:
                        roaster.close_bean_entrance()
                    except:
                        logger.log("Error trying to close bean entrance.")

                current_bean_temperature = int(data["temp_bean"])
                if (
                    not passed_turning_point
                    and seconds > 10
                    and last_bean_temperature < current_bean_temperature
                ):
                    passed_turning_point = True
                    turning_point_temp = current_bean_temperature

                if args.auto:
                    controller.step(
                        seconds, passed_turning_point
                    )  # Set next temperature goal

                    if passed_turning_point:
                        delta_temperature = (
                            last_setup_temperature - current_bean_temperature
                        )

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
                                    logger.log("FECHE A SAÍDA DO MEXEDOR!")

                        # Automatically open bean exit if final temperature is met
                        if last_setup_temperature <= current_bean_temperature:
                            roaster.set_alarm(current_bean_temperature)
                            if not roaster.bean_exit:
                                roaster.set_burner(False)
                                try:
                                    roaster.open_bean_exit()
                                    opened_bean_exit = seconds
                                except:
                                    logger.log("ABRA O TAMBOR!")

                        # Automatically close bean exit after openning it
                        if seconds - opened_bean_exit >= 30:
                            if roaster.bean_exit:
                                try:
                                    roaster.close_bean_exit()
                                except:
                                    logger.log("FECHE O TAMBOR!")

                last_bean_temperature = current_bean_temperature

                if seconds % show_interval == 0:
                    logger.log_stats(data, setup, turning_point_temp)

                finished = time.time() - start_time > total_time
                while time.time() - start_loop <= wait_interval:
                    time.sleep(0.05)

        except KeyboardInterrupt:
            pass

    logger.log("Finalizada a gravação. Fechando conexão e convertendo arquivo... ")
    roaster.close()
    table = rows.import_from_csv(csv_filename)
    rows.export_to_xls(table, xls_filename)
    os.unlink(csv_filename)
    logger.log(f"  Arquivo gravado: {xls_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("numero_torra", type=str)
    parser.add_argument("minutos_totais", type=float)
    parser.add_argument("setup_filename")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--redis", action="store_true")
    parser.add_argument("--fake", action="store_true")
    parser.add_argument(
        "--control_type",
        choices=["bean-temperature", "fire-temperature", "servo-position"],
        default="fire-temperature",
    )
    parser.add_argument("--last_bean_temperature", type=int)
    args = parser.parse_args()

    if args.redis:
        logger = Logger(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT,
            redis_db=settings.REDIS_DB,
            redis_channel=settings.REDIS_CHANNEL,
        )
    else:
        logger = Logger()

    roast(args, logger)
