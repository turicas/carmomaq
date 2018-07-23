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

    def before_start(self):
        self.log('Reprodução será através do servo motor.')
        initial = self.setup['00:00:00']
        self.roaster.set_servo_position(initial.servo_position)

    def after_start(self):
        self.log('Alterando modo de torra para manual (não receita)... ',
                 end=False)
        self.roaster.set_mode('manual')
        self.log('feito!')

    def step(self, seconds, passed_turning_point):
        next_time = utils.pretty_seconds(seconds + 1)
        row = self.setup.get(next_time)
        if not row:  # TODO: if roast is not finished, calculate a proper temp
            return

        self.roaster.set_mode('manual')
        self.roaster.set_servo_position(row.servo_position)


class TemperatureController(Controller):

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
        temp = getattr(initial, self.variable)
        self.roaster.set_setpoint(temp)
        self.roaster.set_servo_position(initial.servo_position)

    def after_start(self):
        self.log('Alterando modo de torra para receita... ', end=False)
        self.roaster.set_mode('recipe')
        self.log('feito!')


class BeanTemperatureController(TemperatureController):

    control_type = 'bean'
    variable = 'temp_bean'

    def step(self, seconds, passed_turning_point):
        next_time = utils.pretty_seconds(seconds + 1)
        row = self.setup.get(next_time)
        if not row:  # TODO: if roast is not finished, calculate a proper temp
            return

        self.roaster.set_mode('recipe')
        self.roaster.set_pid_reference(self.control_type)
        if passed_turning_point:
            self.roaster.set_setpoint(getattr(row, self.variable))


class FireTemperatureController(TemperatureController):

    control_type = 'fire'
    variable = 'temp_fire'

    def step(self, seconds, passed_turning_point):
        next_time = utils.pretty_seconds(seconds + 1)
        row = self.setup.get(next_time)
        if not row:  # TODO: if roast is not finished, calculate a proper temp
            return

        self.roaster.set_mode('recipe')
        self.roaster.set_pid_reference(self.control_type)
        self.roaster.set_setpoint(getattr(row, self.variable))


def get_controller(name):
    return {
        'bean-temperature': BeanTemperatureController,
        'fire-temperature': FireTemperatureController,
        'servo-position': ServoPositionController,
    }[name]
