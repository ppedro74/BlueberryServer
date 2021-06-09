import sys
import threading
import logging
import os
import datetime
import time
import logging
import pigpio
import I2CController

class PiGPIOI2CController(I2CController.I2CController):
    def __init__(self, i2c_ch, log_level):
        super().__init__("PiGPIOI2CController-{}".format(i2c_ch), log_level)
        self.i2c_ch = i2c_ch
        self.pi = pigpio.pi()
        self.handles = dict()

    def get_handle(self, addr):
        if addr not in self.handles:
            self.handles[addr] = self.pi.i2c_open(self.i2c_ch, addr, 0)
        return self.handles[addr]

    def write(self, i2c_addr, data):
        try:
            handle = self.get_handle(i2c_addr)
            self.pi.i2c_write_device(handle, data)
        except Exception as ex:
            self.logger.error("write ex=%s", ex)

    def read(self, i2c_addr, bytes_to_read):
        try:
            handle = self.get_handle(i2c_addr)
            (count, data) = self.pi.i2c_read_device(handle, bytes_to_read)
            if count<0:
                self.logger.warning("read error=%s data_len=%s", count, len(data))
            return data
        except Exception as ex:
            self.logger.error("read ex=%s", ex)

    def stop(self):
        for i2c_addr in self.handles:
            handle = self.handles[addr]
            self.logger.debug("closing handle=%s for i2c_addr=%s", handle, i2c_addr)
            self.pi.i2c_close(handle)

        self.handles = dict()
