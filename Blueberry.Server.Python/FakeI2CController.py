import sys
import threading
import logging
import os
import datetime
import time
import I2CController
import ctypes

I2C_M_RD = 0x0001  # read data, from slave to master

# ctypes versions of I2C structs defined by kernel.
class i2c_msg(ctypes.Structure):
    _fields_ = [('addr',  ctypes.c_uint16),
        ('flags', ctypes.c_uint16),
        ('len',   ctypes.c_uint16),
        ('buf',   ctypes.POINTER(ctypes.c_uint8))]

class i2c_rdwr_ioctl_data(ctypes.Structure):
    _fields_ = [('msgs',  ctypes.POINTER(i2c_msg)),
        ('nmsgs', ctypes.c_uint32)]

def make_i2c_rdwr_data(messages):
    """Utility function to create and return an i2c_rdwr_ioctl_data structure
    populated with a list of specified I2C messages.  The messages parameter
    should be a list of tuples which represent the individual I2C messages to
    send in this transaction.  Tuples should contain 4 elements: address value,
    flags value, buffer length, ctypes c_uint8 pointer to buffer.
    """
    # Create message array and populate with provided data.
    msg_data_type = i2c_msg * len(messages)
    msg_data = msg_data_type()
    for i, m in enumerate(messages):
        msg_data[i].addr = m[0] & 0x7F
        msg_data[i].flags = m[1]
        msg_data[i].len = m[2]
        msg_data[i].buf = m[3]
    # Now build the data structure.
    data = i2c_rdwr_ioctl_data()
    data.msgs = msg_data
    data.nmsgs = len(messages)
    return data

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
        data = bytearray([1] * bytes_to_read) 
        self.logger.debug("read: bytes_to_read:%s => data:%s", bytes_to_read, data)
        return data

    def write_read_data(self, bytes_to_write, number_of_bytes_to_read):
        result_data = bytearray([1] * number_of_bytes_to_read)
        self.logger.debug("write_read_data: bytes_to_write:%s #bytes_to_read:%s => result_data:%s", bytes_to_write, number_of_bytes_to_read, result_data)
        return result_data


class FakeI2CController(I2CController.I2CController):
    def __init__(self, log_level):
        super().__init__("FakeI2CController", log_level)

    def create_slave(self, i2c_addr):
        return FakeI2CSlave(self, i2c_addr)

