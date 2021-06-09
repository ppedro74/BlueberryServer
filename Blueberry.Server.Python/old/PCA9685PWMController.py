import sys
import threading
import logging
import os
import datetime
import time
import math
import logging
import PWMController
import pigpio

class PCA9685PWMController(PWMController.PWMController):
    """
    This class provides an interface to the I2C PCA9685 PWM chip.
    The chip provides 16 PWM channels.
    All channels use the same frequency which may be set in the range 24 to 1526 Hz.
    If used to drive servos the frequency should normally be set in the range 50 to 60 Hz.
    The duty cycle for each channel may be independently set between 0 and 100%.
    It is also possible to specify the desired pulse width in microseconds rather than the duty cycle. This may be more convenient when the chip is used to drive servos.
    The chip has 12 bit resolution, i.e. there are 4096 steps between off and full on.
    """

    _MODE1         = 0x00
    _MODE2         = 0x01
    _SUBADR1       = 0x02
    _SUBADR2       = 0x03
    _SUBADR3       = 0x04
    _PRESCALE      = 0xFE
    _LED0_ON_L     = 0x06
    _LED0_ON_H     = 0x07
    _LED0_OFF_L    = 0x08
    _LED0_OFF_H    = 0x09
    _ALL_LED_ON_L  = 0xFA
    _ALL_LED_ON_H  = 0xFB
    _ALL_LED_OFF_L = 0xFC
    _ALL_LED_OFF_H = 0xFD

    _RESTART = 1<<7
    _AI      = 1<<5
    _SLEEP   = 1<<4
    _ALLCALL = 1<<0

    _OCH    = 1<<3
    _OUTDRV = 1<<2

    def __init__(self, i2c_ch, log_level, i2c_address=0x40):
        super().__init__("PCA9685PWMController", log_level)
        self.pi = pigpio.pi()
        self.i2c_ch = i2c_ch
        self.handle = self.pi.i2c_open(self.i2c_ch, i2c_address, 0)

        self.write_reg(self._MODE1, self._AI | self._ALLCALL)
        self.write_reg(self._MODE2, self._OCH | self._OUTDRV)

        time.sleep(0.0005)

        mode = self.read_reg(self._MODE1)
        self.write_reg(self._MODE1, mode & ~self._SLEEP)

        time.sleep(0.0005)

        self.set_duty_cycle(-1, 0)
        self.set_frequency(1000)

    def get_frequency(self):
        return self.frequency

    def set_frequency(self, frequency):
        prescale = 25000000.0    # 25MHz
        prescale /= 4096.0       # 12-bit
        prescale /= float(frequency)
        prescale -= 1.0
        prescale = int(math.floor(prescale + 0.5))
        if prescale < 3:
            self.logger.debug("prescale=%s adjusted to %s", prescale, 3)
            prescale = 3
        elif prescale > 255:
            self.logger.debug("prescale=%s adjusted to %s", prescale, 255)
            prescale = 255
        mode = self.read_reg(self._MODE1);
        self.write_reg(self._MODE1, (mode & ~self._SLEEP) | self._SLEEP)
        self.write_reg(self._PRESCALE, prescale)
        self.write_reg(self._MODE1, mode)
        time.sleep(0.0005)
        self.write_reg(self._MODE1, mode | self._RESTART)
        self.frequency = (25000000.0 / 4096.0) / (prescale + 1)
        self.pulse_width = (1000000.0 / self.frequency)

    def set_duty_cycle(self, channel, percent):
        "Use -1 for all channels."
        steps = int(round(percent * (4096.0 / 100.0)))
        if steps < 0:
            on = 0
            off = 4096
        elif steps > 4095:
            on = 4096
            off = 0
        else:
            on = 0
            off = steps
        if (channel >= 0) and (channel <= 15):
            self.pi.i2c_write_i2c_block_data(self.handle, self._LED0_ON_L+4*channel, [on & 0xFF, on >> 8, off & 0xFF, off >> 8])
        else:
            self.pi.i2c_write_i2c_block_data(self.handle, self._ALL_LED_ON_L, [on & 0xFF, on >> 8, off & 0xFF, off >> 8])

    def stop(self):
        "Switches all PWM channels off and releases resources."
        self.set_duty_cycle(-1, 0)
        self.pi.i2c_close(self.handle)

    def set_pulse_width(self, channel, width):
        self.set_duty_cycle(channel, (float(width) / self.pulse_width) * 100.0)

    def write_reg(self, reg, byte):
        self.pi.i2c_write_byte_data(self.handle, reg, byte)

    def read_reg(self, reg):
        return self.pi.i2c_read_byte_data(self.handle, reg)

