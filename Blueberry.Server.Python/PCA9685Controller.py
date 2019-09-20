import sys
import threading
import logging
import os
import socket
import datetime
import time
import math
import logging
import PWMController
import ServoController

class PCA9685Controller(PWMController.PWMController):
    """
    This class provides an interface to the I2C PCA9685 PWM chip.
    The chip provides 16 PWM channels.
    All channels use the same frequency which may be set in the range 24 to 1526 Hz.
    If used to drive servos the frequency should normally be set in the range 50 to 60 Hz.
    The duty cycle for each channel may be independently set between 0 and 100%.
    It is also possible to specify the desired pulse width in microseconds rather than the duty cycle. This may be more convenient when the chip is used to drive servos.
    The chip has 12 bit resolution, i.e. there are 4096 steps between off and full on.
    """

    MODE1         = 0x00
    MODE2         = 0x01
    SUBADR1       = 0x02
    SUBADR2       = 0x03
    SUBADR3       = 0x04
    PRESCALE      = 0xFE
    LED0_ON_L     = 0x06
    LED0_ON_H     = 0x07
    LED0_OFF_L    = 0x08
    LED0_OFF_H    = 0x09
    ALL_LED_ON_L  = 0xFA
    ALL_LED_ON_H  = 0xFB
    ALL_LED_OFF_L = 0xFC
    ALL_LED_OFF_H = 0xFD

    RESTART       = 1<<7
    AI            = 1<<5
    SLEEP         = 1<<4
    ALLCALL       = 1<<0

    OCH           = 1<<3
    OUTDRV        = 1<<2

    def __init__(self, i2c_controller, log_level, i2c_address=0x40, osc_clock=25000000):
        super().__init__(self.__class__.__name__+"-"+str(i2c_address), log_level)
        self.i2c_controller = i2c_controller
        self.i2c_address = i2c_address
        self._osc_clock = osc_clock
        self.slave = None

    def stop(self):
        #Switches all PWM ports off
        self.set_duty_cycle(-1, 0)
        self.slave.close()

    def start(self):
        self.slave = self.i2c_controller.get_slave(self.i2c_address)
        self.slave.write_reg_byte(self.MODE1, self.AI | self.ALLCALL)
        self.slave.write_reg_byte(self.MODE2, self.OCH | self.OUTDRV)
        time.sleep(0.0005)
        mode = self.slave.read_reg_byte(self.MODE1)
        self.slave.write_reg_byte(self.MODE1, mode & ~self.SLEEP)
        time.sleep(0.0005)
        #default pwm frequency
        self.frequency = 60

    @property
    def frequency(self):
        return (self._osc_clock / 4096.0) / (self._prescale + 1)

    @frequency.setter
    def frequency(self, value):
        self._prescale = self._osc_clock
        self._prescale /= 4096.0  # 12-bit
        self._prescale /= float(value)
        self._prescale -= 1.0
        self._prescale = int(math.floor(self._prescale + 0.5))
        if self._prescale < 3:
            self.logger.debug("self._prescale=%s adjusted to %s", self._prescale, 3)
            self._prescale = 3
        elif self._prescale > 255:
            self.logger.debug("self._prescale=%s adjusted to %s", self._prescale, 255)
            self._prescale = 255
        mode = self.slave.read_reg_byte(self.MODE1);
        self.slave.write_reg_byte(self.MODE1, (mode & ~self.SLEEP) | self.SLEEP)
        self.slave.write_reg_byte(self.PRESCALE, self._prescale)
        self.slave.write_reg_byte(self.MODE1, mode)
        time.sleep(0.005)
        self.slave.write_reg_byte(self.MODE1, mode | self.RESTART)
        self.pulse_width_us = (1000000.0 / self.frequency)
        self.logger.debug ("freq=%s pulse_width=%s (us per bit)", self.frequency, self.pulse_width_us)

    def set_duty_cycle(self, port, value, max_value=100):
        #Use -1 for all ports.

        if max_value == 4096:
            steps = int(value)
        else:
            steps = int(round(value * (4096.0 / max_value)))
        if steps < 0:
            on = 0
            off = 4096
        elif steps >= 4096:
            on = 4096
            off = 0
        else:
            on = 0
            off = steps
        self.logger.debug("set_duty_cycle port=%s value=%s max_value=%s on=%s off=%s", port, value, max_value, on, off)
        if (port >= 0) and (port <= 15):
            data = [self.LED0_ON_L+4*port, on & 0xFF, on >> 8, off & 0xFF, off >> 8]
            self.slave.write(bytearray(data))
        elif port==-1:
            data = [self.ALL_LED_ON_L, on & 0xFF, on >> 8, off & 0xFF, off >> 8]
            self.slave.write(bytearray(data))

    def set_pulse_width(self, channel, width_in_us):
        #self.set_duty_cycle(channel, (float(width_in_us) / self.pulse_width_us) * 100.0)
        steps = round((width_in_us * 4096)/self.pulse_width_us)
        self.set_duty_cycle(channel, steps, 4096)

class PCA9685ServoController(PCA9685Controller, ServoController.ServoController):
    def __init__(self, i2c_controller, log_level, i2c_address=0x40, osc_clock=25000000):
        self._started = False
        PCA9685Controller.__init__(self, i2c_controller, log_level, i2c_address, osc_clock)

    def start(self):
        super().start()
        #servo frequency
        #PCA9685Controller.frequency.fset(self, 50)
        self.frequency = 50
        self._started = True

    @PCA9685Controller.frequency.setter
    def frequency(self, value):
        if self._started:
            raise NotImplementedError("frequency cannot be set on servo controller")
        PCA9685Controller.frequency.fset(self, value)

    def release(self, port):
        self.set_duty_cycle(port, 0)
        super().release(port)

    def set_position(self, port, position_in_us):
        super().set_position(port, position_in_us)
        self.set_pulse_width(port, position_in_us)

    def set_speed(self, port, speed):
        pass



def test():
    if sys.platform == "linux" or sys.platform == "linux2":
        import DeviceI2CController
        i2c_com = DeviceI2CController.DeviceI2CController(1, logging.DEBUG)
    else:
        import FakeI2CController
        i2c_com = FakeI2CController.FakeI2CController(logging.DEBUG)
    i2c_com.start()

    pwm_ctrl = PCA9685Controller(i2c_com, logging.DEBUG)
    pwm_ctrl.start()
    p4 = PWMController.PWMPort(pwm_ctrl, 4)
    p4.set_duty_cycle(25)
    p5 = PWMController.PWMPort(pwm_ctrl, 5)
    p5.set_duty_cycle(50)
    p6 = PWMController.PWMPort(pwm_ctrl, 6)
    p6.set_duty_cycle(75)
    pwm_ctrl.stop()

    #servo_ctrl = PCA9685ServoController(i2c_com, logging.DEBUG)
    #servo_ctrl.start()
    #s0 = ServoController.ServoPort(servo_ctrl, 0, 560, 2140)
    #s0.set_position(90)
    #s1 = ServoController.ServoPort(servo_ctrl, 1, 560, 2140)
    #s1.set_position(90)
    #servo_ctrl.stop()


if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting... platform=%s hostname=%s", sys.platform, socket.gethostname())
    
    test()

    input("===> Press Enter to quit...\n")
