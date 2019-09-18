import sys
import logging
import ServoController

class PimoroniPanTiltHatServoController(ServoController.ServoController):
    PWM = 0
    WS2812 = 1

    RGB = 0
    GRB = 1
    RGBW = 2
    GRBW = 3
    
    REG_CONFIG = 0x00
    REG_SERVO1 = 0x01
    REG_SERVO2 = 0x03
    REG_WS2812 = 0x05
    REG_UPDATE = 0x4E
    
    UPDATE_WAIT = 0.03
    
    def __init__(self, i2c_controller, log_level, i2c_address=0x15):
        super().__init__("PimoroniPanTiltHatServoController", log_level)
        self.i2c_controller = i2c_controller
        self.i2c_address = i2c_address
        self.slave = None

        self._enable_servo1 = False
        self._enable_servo2 = False
        self._enable_lights = False
        self._light_mode = self.WS2812
        self._light_on = 0

    def start(self):
        self.slave = self.i2c_controller.get_slave(self.i2c_address)
        self._set_config()

    def stop(self):
        self.slave.close()
    
    def release(self, port):
        self.logger.debug("release port=%s", port)

        if port == 0:
            self._enable_servo1 = state
        else:
            self._enable_servo2 = state

        self._set_config()

    def set_position(self, port, position_in_us):
        has_changes = False
        if port == 0:
            reg = self.REG_SERVO1
            if not self._enable_servo1:
                self._enable_servo1 = True
                has_changes = True
        elif port == 1:
            reg = self.REG_SERVO2
            if not self._enable_servo2:
                self._enable_servo2 = True
                has_changes = True
        else:
            return
        if has_changes:
            self._set_config()
        self.slave.write_reg_word(reg, position_in_us)

    def set_speed(self, port, speed):
        pass

    def _set_config(self):
        """Generate config value for PanTilt HAT and write to device."""
        config = 0
        config |= self._enable_servo1
        config |= self._enable_servo2 << 1
        config |= self._enable_lights << 2
        config |= self._light_mode    << 3
        config |= self._light_on      << 4
        self.slave.write_reg_byte(self.REG_CONFIG, config)

