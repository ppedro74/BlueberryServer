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
import DigitalController

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

    def __init__(self, i2c_controller, log_level, i2c_address=0x40):
        super().__init__("PCA9685Controller-"+str(i2c_address), log_level)
        self.i2c_controller = i2c_controller
        self.i2c_address = i2c_address
        self.slave = None

    def stop(self):
        "Switches all PWM channels off and releases resources."
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
        self.set_duty_cycle(-1, 0)
        self.set_frequency(60)

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
        mode = self.slave.read_reg_byte(self.MODE1);
        self.slave.write_reg_byte(self.MODE1, (mode & ~self.SLEEP) | self.SLEEP)
        self.slave.write_reg_byte(self.PRESCALE, prescale)
        self.slave.write_reg_byte(self.MODE1, mode)
        time.sleep(0.0005)
        self.slave.write_reg_byte(self.MODE1, mode | self.RESTART)
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
            data = [self.LED0_ON_L+4*channel, on & 0xFF, on >> 8, off & 0xFF, off >> 8]
            self.slave.write(bytearray(data))
        else:
            data = [self.ALL_LED_ON_L, on & 0xFF, on >> 8, off & 0xFF, off >> 8]
            self.slave.write(bytearray(data))

    def set_pulse_width(self, channel, width):
        self.set_duty_cycle(channel, (float(width) / self.pulse_width) * 100.0)

def test():
    import DeviceI2CController
    i2c_com = DeviceI2CController.DeviceI2CController(1, logging.DEBUG)
    i2c_com.start()

    com = PCA9685Controller(i2c_com, logging.DEBUG)
    com.start()

    p4 = PWMController.PWMPort(com, 4)
    p4.set_duty_cycle(100)

    p5 = PWMController.PWMPort(com, 5)
    p5.set_duty_cycle(0)

    p6 = PWMController.PWMPort(com, 6)
    p6.set_duty_cycle(100)

if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting... platform=%s hostname=%s", sys.platform, socket.gethostname())
    
    test()

    input("===> Press Enter to quit...\n")
