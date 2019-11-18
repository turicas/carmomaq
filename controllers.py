import time

import utils


class Controller:

    def __init__(self, roaster, setup):
        self.roaster = roaster
        self.setup = setup

    def log(self, message, end=True):
        message = '  ' + message
        if end:
            print(message)
        else:
            print(message, end='', flush=True)

    def before_start(self):
        raise NotImplementedError()

    def after_start(self):
        raise NotImplementedError()


class ServoPositionController(Controller):

    variable = "servo_position"
    seconds_ahead = 1

    def before_start(self):
        self.log('Reprodução será através do servo motor.')
        initial = self.setup['00:00:00']
        self.roaster.set_servo_position(getattr(initial, self.variable))

    def after_start(self):
        self.log('Alterando modo de torra para manual (não receita)... ',
                 end=False)
        self.roaster.set_mode('manual')
        self.log('feito!')

    def step(self, seconds, passed_turning_point):
        row = utils.get_last_setup_for(self.setup, seconds + self.seconds_ahead, self.variable)
        self.roaster.set_mode('manual')
        self.roaster.set_servo_position(getattr(row, self.variable))


class TemperatureController(Controller):

    seconds_ahead = 1

    def before_start(self):
        if not getattr(self, 'variable', None):
            raise ValueError('Missing self.variable')
        if not getattr(self, 'control_type', None):
            raise ValueError('Missing self.control_type')
        elif self.control_type not in ('bean', 'fire'):
            raise ValueError('Wrong self.control_type')

        self.log(f'Alterando PID para seguir: {self.variable}... ', end=False)
        self.roaster.set_pid_reference(self.control_type)
        self.log('feito!')

        initial = self.setup['00:00:00']
        self.log(f"Alterando posição inicial do servo para: {initial.servo_position}...", end=False)
        temp = getattr(initial, self.variable)
        current_servo_position = self.roaster.data["servo_position"]
        self.roaster.set_setpoint(temp)
        self.roaster.set_servo_position(initial.servo_position)
        # For each percent the servo needs to turn, it waits 1 second
        # TODO: use more accurate measure if the servo is in the right position
        time.sleep(
            abs(initial.servo_position - current_servo_position)
        )
        self.log("feito (espero)!")

    def after_start(self):
        self.log('Alterando modo de torra para receita... ', end=False)
        self.roaster.set_mode('recipe')
        self.log('feito!')


class BeanTemperatureController(TemperatureController):

    control_type = 'bean'
    variable = 'temp_bean'

    def step(self, seconds, passed_turning_point):
        row = utils.get_last_setup_for(self.setup, seconds + self.seconds_ahead, self.variable)
        self.roaster.set_mode('recipe')
        self.roaster.set_pid_reference(self.control_type)
        if passed_turning_point:
            self.roaster.set_setpoint(getattr(row, self.variable))


class FireTemperatureController(TemperatureController):

    control_type = 'fire'
    variable = 'temp_fire'
    seconds_ahead = 30

    def step(self, seconds, passed_turning_point):
        row = utils.get_last_setup_for(self.setup, seconds + self.seconds_ahead, self.variable)
        self.roaster.set_mode('recipe')
        self.roaster.set_pid_reference(self.control_type)
        self.roaster.set_setpoint(getattr(row, self.variable))


def get_controller(name):
    return {
        'bean-temperature': BeanTemperatureController,
        'fire-temperature': FireTemperatureController,
        'servo-position': ServoPositionController,
    }[name]
