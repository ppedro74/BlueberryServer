import logging
import threading
import Controller

class I2CSlave:
    def __init__(self, controller, i2c_addr):
        self.controller = controller
        self.i2c_addr = i2c_addr
        self.logger = logging.getLogger("{}-{}".format(controller.name, i2c_addr))
        self.logger.setLevel(controller.log_level)

    def __del__(self):
        self.close()

    def close(self):
        pass

    def write(self, data):
        pass

    def read(self, bytes_to_read):
        return None

    def write_read_data(self, byte_to_write, bytes_to_read):
        return None

    def write_reg_byte(self, reg_u8, data_u8):
        data = bytearray(2)
        data[0] = reg_u8
        data[1] = data_u8
        self.write(data)

    def write_reg_word(self, reg_u8, data_u16):
        data = bytearray()
        data.append(reg_u8)
        data += data_u16.to_bytes(2, "little")
        self.write(data)

    def read_reg_byte(self, reg_u8):
        data = self.write_read_data(reg_u8, 1)
        return data[0]


class I2CController(Controller.Controller):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.slaves = dict()
        self.lock = threading.Lock()

    def get_slave(self, i2c_addr):
        return None

    def write(self, i2c_addr, data):
        slave = self.get_slave(i2c_addr)
        if slave is None:
            self.logger.error("write: slave addr=%s not available", i2c_addr)
            return
        slave.write(data)

    def read(self, i2c_addr, bytes_to_read):
        slave = self.get_slave(i2c_addr)
        if slave is None:
            self.logger.error("read: slave addr=%s not available", i2c_addr)
            return bytes()
        return slave.read(bytes_to_read)

    def stop(self):
        self.lock.acquire()
        try:
            for i2c_addr in self.slaves:
                self.logger.debug("closing slave=%s", i2c_addr)
                self.slaves[i2c_addr].close()

            self.slaves = dict()
        finally:
            self.lock.release()
