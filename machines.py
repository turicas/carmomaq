import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp


class CarmoMaq10:

    # TODO: refactor toggles to properties
    TIME_BEAN_ENTRANCE_PISTON = 6
    TIME_BEAN_EXIT_PISTON = 9
    TIME_COOLER_EXIST_PISTON = 9.5
    TIME_BEAN_ENTRANCE_PISTON = 6
    ADDR_READ_BEAN_ENTRANCE = 16005
    ADDR_READ_BEAN_EXIT = 16007
    ADDR_READ_COOLER_EXIT = 16008
    ADDR_WRITE_BEAN_ENTRANCE = 49983
    ADDR_WRITE_BEAN_EXIT = 49982
    ADDR_WRITE_COOLER_EXIT = 49981
    ADDR_ALARM = 28110
    ADDR_BURNER = 49995
    ADDR_CYLINDER = 49991
    ADDR_COOLER = 49993
    ADDR_MIXER = 49994
    ADDR_OPERATIONAL_MODE = 49996
    ADDR_PID_D = 30002
    ADDR_PID_I = 30001
    ADDR_PID_P = 30000
    ADDR_RECIPE_MIN_START = 28010
    ADDR_RECIPE_SEC_START = 28201
    ADDR_RECIPE_TEMP_START = 28040
    ADDR_SERVO_POSITION = 28240
    ADDR_SETPOINT = 8003
    ADDR_START_ROAST = 49998
    ADDR_PID_REFERENCE = 55556

    def __init__(self, host='192.168.0.10', port=502):
        self.host = host
        self.port = port

    def connect(self, timeout=5.0):
        """Start the modbus connection with the roaster"""

        self._master = modbus_tcp.TcpMaster(self.host, self.port)
        self._master.set_timeout(timeout)

    def _read_bools(self, start_address, quantity):
        """Read consecutive boolean values"""

        result = self._master.execute(
            1,
            cst.READ_COILS,
            start_address,
            quantity,
        )
        return [True if value == 1 else False for value in result]

    def _read_words(self, start_address, quantity):
        """Read consecutive word values"""

        return self._master.execute(
            1,
            cst.READ_HOLDING_REGISTERS,
            start_address,
            quantity,
        )

    def _write_bool(self, coil_address, value):
        """Write a single bool value to a specific address"""

        assert value in (0, 1)
        self._master.execute(
            1,
            cst.WRITE_SINGLE_COIL,
            coil_address,
            output_value=value,
        )

    def _write_word(self, register_address, value):
        """Write a single word value to a specific address"""

        self._master.execute(
            1,
            cst.WRITE_SINGLE_REGISTER,
            register_address,
            output_value=value
        )

    def _write_words(self, start_address, values):
        """Write consecutive word values to consecutive addresses"""

        self._master.execute(
            1,
            cst.WRITE_MULTIPLE_REGISTERS,
            start_address,
            output_value=values,
        )

    def _get_status(self, address):
        """Get value and convert to bool (useful for toggle options)"""

        value = self._read_bools(address, 1)[0]
        return True if value == 1 else False

    def _set_status(self, address, status):
        """Set status based on a bool value (useful for toggle options)"""

        assert status in (True, False)
        self._write_bool(address, 1 if status else 0)

    @property
    def bean_entrance(self):
        return self._get_status(self.ADDR_READ_BEAN_ENTRANCE)

    def open_bean_entrance(self):
        assert not any([self.bean_exit, self.cooler_exit])
        assert not self.bean_entrance
        self._set_status(self.ADDR_WRITE_BEAN_ENTRANCE, True)

    def close_bean_entrance(self):
        assert all([not self.bean_exit, not self.cooler_exit])
        assert self.bean_entrance
        self._set_status(self.ADDR_WRITE_BEAN_ENTRANCE, False)

    @property
    def bean_exit(self):
        return self._get_status(self.ADDR_READ_BEAN_EXIT)

    def open_bean_exit(self):
        assert not any([self.bean_entrance, self.cooler_exit])
        assert not self.bean_exit
        self._set_status(self.ADDR_WRITE_BEAN_EXIT, True)

    def close_bean_exit(self):
        assert all([not self.bean_entrance, not self.cooler_exit])
        assert self.bean_exit
        self._set_status(self.ADDR_WRITE_BEAN_EXIT, False)

    @property
    def cooler_exit(self):
        return self._get_status(self.ADDR_READ_COOLER_EXIT)

    def open_cooler_exit(self):
        assert not any([self.bean_entrance, self.bean_exit])
        assert not self.cooler_exit
        self._set_status(self.ADDR_WRITE_COOLER_EXIT, True)

    def close_cooler_exit(self):
        assert all([not self.bean_entrance, not self.bean_exit])
        assert self.cooler_exit
        self._set_status(self.ADDR_WRITE_COOLER_EXIT, False)

    def set_alarm(self, temperature):
        # TODO: add property to get current value
        assert isinstance(temperature, int) and temperature > 0
        self._write_word(self.ADDR_ALARM, temperature)

    def set_servo_position(self, position):
        # TODO: add property to get current value
        assert isinstance(position, (int, float)) and 0 <= position <= 100
        self._write_word(self.ADDR_SERVO_POSITION, int(position))

    @property
    def pid_reference(self):
        value = self._read_bools(self.ADDR_PID_REFERENCE, 1)[0]

        if value is False:
            return 'bean'
        elif value is True:
            return 'fire'

    def set_pid_reference(self, reference):
        # TODO: test
        # TODO: add property to get current value
        if reference not in ('bean', 'fire'):
            raise ValueError("'reference' must be 'bean' or 'fire'")

        if reference == 'bean':
            self._write_bool(self.ADDR_PID_REFERENCE, False)
        elif reference == 'fire':
            self._write_bool(self.ADDR_PID_REFERENCE, True)

    @property
    def pid_parameters(self):
        return self._read_words(self.ADDR_PID_P, 3)

    def set_pid_parameters(self, p_value, i_value, d_value):
        assert isinstance(p_value, int)
        assert isinstance(i_value, int)
        assert isinstance(d_value, int)
        self._write_word(self.ADDR_PID_P, p_value)
        self._write_word(self.ADDR_PID_I, i_value)
        self._write_word(self.ADDR_PID_D, d_value)

    @property
    def mode(self):
        value = self._read_bools(self.ADDR_OPERATIONAL_MODE, 1)[0]
        return 'recipe' if value == False else 'manual'

    def set_mode(self, mode):
        if mode not in ('manual', 'recipe'):
            raise ValueError("'mode' must be 'recipe' or 'manual'")

        if mode == 'recipe':
            self._write_bool(self.ADDR_OPERATIONAL_MODE, 0)  # recipe
        else:
            self._write_bool(self.ADDR_OPERATIONAL_MODE, 1)  # manual

    def start_roast(self):
        data = self.data
        if data['roasting']:
            return

        self._write_bool(self.ADDR_START_ROAST, 0)
        self._write_bool(self.ADDR_START_ROAST, 1)

    def stop_roast(self):
        data = self.data
        if not data['roasting']:
            return

        self._write_bool(self.ADDR_START_ROAST, 0)
        self._write_bool(self.ADDR_START_ROAST, 1)

    def set_setpoint(self, temperature):
        # TODO: add property to get current value
        assert isinstance(temperature, int) and temperature > 0
        self._write_word(self.ADDR_SETPOINT, temperature)

    @property
    def mixer(self):
        return self._get_status(self.ADDR_MIXER)

    def set_mixer(self, status):
        self._set_status(self.ADDR_MIXER, status)

    @property
    def cooler(self):
        return self._get_status(self.ADDR_COOLER)

    def set_cooler(self, status):
        self._set_status(self.ADDR_COOLER, status)

    @property
    def burner(self):
        return self._get_status(self.ADDR_BURNER)

    def set_burner(self, status):
        self._set_status(self.ADDR_BURNER, status)

    @property
    def cylinder(self):
        return self._get_status(self.ADDR_CYLINDER)

    def set_cylinder(self, status):
        if not status:  # prevent the cylinder from burning because not moving
            self.set_burner(False)

        self._set_status(self.ADDR_CYLINDER, status)

    def clear_recipe(self):
        # TODO: add property to get current value
        self._write_words(self.ADDR_RECIPE_MIN_START, [0] * 30)
        self._write_words(self.ADDR_RECIPE_SEC_START, [0] * 30)
        self._write_words(self.ADDR_RECIPE_TEMP_START, [0] * 30)

    @property
    def data(self):
        """Get current sensor data"""

        # TODO: refactor
        header_1 = (
                'temp_bean', 'temp_air', 'temp_fire', 'temp_goal',
                '_', '_',
                'roast_time', 'roast_minutes', 'roast_seconds',
                '_',
                'temp_cooler',
                'servo_position',
        )
        response_1 = self._read_words(8000, 12)
        header_2 = (
            '_',
            'powered',
            '_',
            '_',
            '_',
            'burner',
            '_',
            '_',
            '_',
            'roasting',
        )
        response_2 = self._read_bools(49990, 10)
        data = dict(zip(header_1, response_1))
        data.update(dict(zip(header_2, response_2)))
        del data['roast_minutes']
        del data['roast_seconds']
        del data['_']
        data['roast_time'] = int(data['roast_time'])
        data['servo_position'] = int(data['servo_position'] / 10.0)
        data['roasting'] = True if data['roasting'] == 1 else False
        return data

    def close(self):
        """Close modbus connection"""

        self._master.close()
