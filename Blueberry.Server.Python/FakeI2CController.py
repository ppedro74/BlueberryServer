import sys
import threading
import logging
import os
import datetime
import time
import I2CController

class FakeI2CSlave(I2CController.I2CSlave):

    def __init__(self, controller, i2c_addr):
        super().__init__(controller, i2c_addr) 
        self.logger.debug("opened")

    def close(self):
        self.logger.debug("closed")
        super().close()

    def write(self, data):
        try:
            self.logger.debug("write: dec=%s hex=%s", list(data), [hex(x) for x in list(data)])
        except Exception as ex:
            self.logger.error("writing: ex=%s", ex)

    def read(self, bytes_to_read):
        data = bytearray(bytes_to_read)
        self.logger.debug("read: bytes_to_read:%s => data:%s", bytes_to_read, data)
        return data

    def write_read_data(self, byte_to_write, bytes_to_read):
        data = bytearray(bytes_to_read)
        self.logger.debug("write_read_data: byte_to_write:%s bytes_to_read:%s => data:%s", byte_to_write, bytes_to_read, data)
        return data


class FakeI2CController(I2CController.I2CController):
    def __init__(self, log_level):
        super().__init__("FakeI2CController", log_level)

    def create_slave(self, i2c_addr):
        return FakeI2CSlave(self, i2c_addr)

