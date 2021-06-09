import sys
import threading
import logging
import os
import datetime
import time
import logging
import smbus
import I2CController

class SMBUSI2CController(I2CController.I2CController):
    def __init__(self, i2c_ch, log_level):
        super().__init__("SMBUSI2CController-{}".format(i2c_ch), log_level)
        self.i2c_ch = i2c_ch
        self.bus = smbus.SMBus(i2c_ch)
        self.lock = threading.Lock()
        self.last_cmd = None

    def send_last_cmd_callback(self):
        self.lock.acquire()
        try:
            self.send_last_cmd()
        finally:
            self.lock.release()

    def send_last_cmd(self):
        if self.last_cmd is not None:
            (i2c_addr, cmd) = self.last_cmd
            self.bus.write_byte(i2c_addr, cmd)
            self.last_cmd = None

    def write(self, i2c_addr, data):
        cmd = data[0]
        if len(data)>1:
            data = bytes(data[1:])
            self.logger.debug("write cmd=%s data=%s", cmd, data)
            self.bus.write_i2c_block_data(i2c_addr, cmd, data)
        else:
            # we are guessing a call to write with a single byte represents the cmd of a future read command
            self.lock.acquire()
            try:
                self.send_last_cmd()

                self.logger.debug("deferred write possible cmd=%s", cmd)
                self.last_cmd = (i2c_addr, cmd)
                timer = threading.Timer(1, self.send_last_cmd_callback)

            finally:
                self.lock.release()

    def read(self, i2c_addr, bytes_to_read):
        self.lock.acquire()
        try:
            last_cmd = self.last_cmd
            self.last_cmd = None
        finally:
            self.lock.release()

        if last_cmd is None:
            self.logger.warning("can't determine cmd value, request will be ignored")
            return bytes(0)
        elif last_cmd[0]!=i2c_addr:
            self.logger.warning("can't determine cmd value, previous_addr=%s current_addr=%s request will be ignored", last_cmd[0], i2c_addr)
            return bytes(0)
        
        self.logger.debug("read addr=%s cmd=%s bytes_to_read=%s", i2c_addr, last_cmd[1], bytes_to_read)
        return self.bus.read_i2c_block_data(i2c_addr, last_cmd[1], bytes_to_read)
