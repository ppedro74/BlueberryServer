import io
import logging
import fcntl
import I2CController
import ctypes

# I2C C API constants (from linux kernel headers)
I2C_M_TEN             = 0x0010  # this is a ten bit chip address
I2C_M_RD              = 0x0001  # read data, from slave to master
I2C_M_STOP            = 0x8000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NOSTART         = 0x4000  # if I2C_FUNC_NOSTART
I2C_M_REV_DIR_ADDR    = 0x2000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_IGNORE_NAK      = 0x1000  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NO_RD_ACK       = 0x0800  # if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_RECV_LEN        = 0x0400  # length will be first received byte

I2C_SLAVE             = 0x0703  # Use this slave address
I2C_SLAVE_FORCE       = 0x0706  # Use this slave address, even if
                                # is already in use by a driver!
I2C_TENBIT            = 0x0704  # 0 for 7 bit addrs, != 0 for 10 bit
I2C_FUNCS             = 0x0705  # Get the adapter functionality mask
I2C_RDWR              = 0x0707  # Combined R/W transfer (one STOP only)
I2C_PEC               = 0x0708  # != 0 to use PEC with SMBus
I2C_SMBUS             = 0x0720  # SMBus transfer


# ctypes versions of I2C structs defined by kernel.
class i2c_msg(ctypes.Structure):
    _fields_ = [
        ('addr',  ctypes.c_uint16),
        ('flags', ctypes.c_uint16),
        ('len',   ctypes.c_uint16),
        ('buf',   ctypes.POINTER(ctypes.c_uint8))
    ]

class i2c_rdwr_ioctl_data(ctypes.Structure):
    _fields_ = [
        ('msgs',  ctypes.POINTER(i2c_msg)),
        ('nmsgs', ctypes.c_uint32)
    ]


def make_i2c_rdwr_data(messages):
    """Utility function to create and return an i2c_rdwr_ioctl_data structure
    populated with a list of specified I2C messages.  The messages parameter
    should be a list of tuples which represent the individual I2C messages to
    send in this transaction.  Tuples should contain 4 elements: address value,
    flags value, buffer length, ctypes c_uint8 pointer to buffer.
    """
    # Create message array and populate with provided data.
    msg_data_type = i2c_msg*len(messages)
    msg_data = msg_data_type()
    for i, m in enumerate(messages):
        msg_data[i].addr  = m[0] & 0x7F
        msg_data[i].flags = m[1]
        msg_data[i].len   = m[2]
        msg_data[i].buf   = m[3]
    # Now build the data structure.
    data = i2c_rdwr_ioctl_data()
    data.msgs  = msg_data
    data.nmsgs = len(messages)
    return data


class DeviceI2CSlave(I2CController.I2CSlave):

    def __init__(self, controller, i2c_addr, fd):
        super().__init__(controller, i2c_addr) 
        self.fd = fd

    def close(self):
        if self.fd is None:
            return
        try:
            self.fd.close()
            self.fd = None
        except Exception as ex:
            self.logger.error("closing: ex=%s", ex)

    def write(self, data):
        try:
            self.logger.debug("write: %s", data)
            self.fd.write(bytes(data))
        except Exception as ex:
            self.logger.error("writing: ex=%s", ex)

    def read(self, bytes_to_read):
        try:
            data = self.fd.read(bytes_to_read)
            self.logger.debug("read: bytes_to_read:%s => data:%s", bytes_to_read, data)
            return data
        except Exception as ex:
            self.logger.error("reading: ex=%s", ex)
        return bytes()

    def write_read_data(self, byte_to_write, bytes_to_read):
        # Build ctypes values to marshall between ioctl and Python.
        reg = ctypes.c_uint8(byte_to_write)
        result = ctypes.create_string_buffer(bytes_to_read) #From ctypes
        request = make_i2c_rdwr_data([
            (self.i2c_addr, 0, 1, ctypes.pointer(reg)), # Write cmd register.
            (self.i2c_addr, I2C_M_RD, bytes_to_read, ctypes.cast(result, ctypes.POINTER(ctypes.c_uint8))) # Read data.
        ])
        fcntl.ioctl(self.fd, I2C_RDWR, request)
        data = bytearray(result.raw)  # Use .raw instead of .value which will stop at a null byte!
        self.logger.debug("write_read_data: byte_to_write:%s bytes_to_read:%s => data:%s", byte_to_write, bytes_to_read, data)
        return data

class DeviceI2CController(I2CController.I2CController):
   
    def __init__(self, bus, log_level):
        super().__init__("DeviceI2CController-{}".format(bus), log_level)
        self.bus = bus

    def get_slave(self, i2c_addr):
        self.lock.acquire()
        try:
            if i2c_addr not in self.slaves:
                try:
                    dev_name = "/dev/i2c-"+str(self.bus)
                    fd = io.open(dev_name, "r+b", buffering=0)
                    #self.logger.debug("opened: dev_name:%s fd:%s addr:%s", dev_name, fd, i2c_addr)

                    fcntl.ioctl(fd, I2C_SLAVE, i2c_addr)
                    slave = DeviceI2CSlave(self, i2c_addr, fd)
                    self.slaves[i2c_addr] = slave
                except Exception as ex:
                    self.logger.error("opening: ex=%s", ex)
                    return None
            
            return self.slaves[i2c_addr]
        finally:
            self.lock.release()

