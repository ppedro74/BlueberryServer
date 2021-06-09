import sys
import logging
import time
import ctypes
import struct
import threading
import Controller
import TcpServer

#Page 20
class REGISTER_MAP:
    PCTL            = 0x00 # Power control
    RST             = 0x01 # Reset
    FPSC            = 0x02 # Frame Rate
    INTC            = 0x03 # INT control
    STAT            = 0x04 # Status
    SCLR            = 0x05 # Status clear
    _RESERVED       = 0x06 # Reserved
    AVE             = 0x07 # Average
    INTHL           = 0x08 # Interrupt Level upper limit setting bits 0:7
    INTHH           = 0x09 # Interrupt Level upper limit setting bits 8:11
    INTLL           = 0x0A # Interrupt Level lower limit setting bits 0:7
    INTLH           = 0x0B # Interrupt Level lower limit setting bits 8:11
    IHYSL           = 0x0C # Setting of Interrupt Hysteresis Level bits 0:7
    IHYSH           = 0x0D # Setting of Interrupt Hysteresis Level bits 8:11
    T00L            = 0x0E # Thermistor Output Value Lower Level
    T00H            = 0x0F # Thermistor Output Value Upper Level
    INT0            = 0x010 # Pixel 1～8   Interrupt Result
    INT1            = 0x011 # Pixel 9～16  Interrupt Result
    INT2            = 0x012 # Pixel 17～24 Interrupt Result
    INT3            = 0x013 # Pixel 25～32 Interrupt Result
    INT4            = 0x014 # Pixel 33～40 Interrupt Result
    INT5            = 0x015 # Pixel 41～48 Interrupt Result
    INT6            = 0x016 # Pixel 49～56 Interrupt Result
    INT7            = 0x017 # Pixel 57～64 Interrupt Result
    PIXEL01_OUTPUT_L = 0x80 # Pixel 1 Output Value Lower Level
    PIXEL01_OUTPUT_H = 0x81 # Pixel 1 Output Value Upper Level
    PIXEL09_OUTPUT_L = 0x90
    PIXEL09_OUTPUT_H = 0x91
    PIXEL17_OUTPUT_L = 0xA0
    PIXEL17_OUTPUT_H = 0xA1
    PIXEL25_OUTPUT_L = 0xB0
    PIXEL25_OUTPUT_H = 0xB1
    PIXEL33_OUTPUT_L = 0xC0
    PIXEL33_OUTPUT_H = 0xC1
    PIXEL41_OUTPUT_L = 0xD0
    PIXEL41_OUTPUT_H = 0xD1
    PIXEL49_OUTPUT_L = 0xE0
    PIXEL49_OUTPUT_H = 0xE1
    PIXEL57_OUTPUT_L = 0xF0
    PIXEL57_OUTPUT_H = 0xF1
    PIXEL64_OUTPUT_L = 0xFE # Pixel 64 Output Value Lower Level
    PIXEL64_OUTPUT_H = 0xFF # Pixel 64 Output Value Upper Level

#Page 13
class PCTL:
    REGISTER        = REGISTER_MAP.PCTL
    NORMAL_MODE     = 0x00
    SLEEP_MODE      = 0x10
    STAND_BY_60_SEC = 0x20
    STAND_BY_10_SEC = 0x21

#Page 14
class RST:
    REGISTER        = REGISTER_MAP.RST
    FLAG_RESET      = 0x30
    INITIAL_RESET   = 0x3F

#Page 14
class FPSC:
    REGISTER        = REGISTER_MAP.FPSC
    FPS_10          = 0x00
    FPS_1           = 0x01

#Page 14
class INTC:
    REGISTER        = REGISTER_MAP.INTC
    INT_DISABLED    = 0x00   # INT Output reactive（Hi-Z）
    INT_ENABLED     = 1 << 0 # INT Output active
    INT_MOD_DIFF    = 0x00   # Difference Interrupt Mode
    INT_MOD_ABS     = 1 << 1 # Absolute Value Interrupt Mode

#Page 15
class STAT:
    REGISTER        = REGISTER_MAP.STAT
    INTF            = 1 << 1 # Interrupt Outbreak
    OVF_IRS         = 1 << 2 # Temperature Output Overflow
    OVF_THS         = 1 << 3 # Thermistor Temperature Output Overflow

#Page 15
class SCLR:
    REGISTER        = REGISTER_MAP.SCLR
    INTCLR          = 1 << 1 # Interrupt Flag Clear
    OVS_CLR         = 1 << 2 # Temperature Output Overflow Flag Clear
    OVT_CLR         = 1 << 3 # Thermistor Temperature Output Overflow Flag Clear

#Page 16
class AVE:
    REGISTER        = REGISTER_MAP.AVE
    MAMOD           = 1 << 5 # Twice moving average output mode


class GridEyeController(Controller.Controller):
    def __init__(self, i2c_controller, log_level, tcp_server=None, i2c_address=0x68):
        super().__init__(self.__class__.__name__ + "-" + str(i2c_address), log_level)
        self.i2c_controller = i2c_controller
        self.i2c_address = i2c_address
        self.server = tcp_server
        self.slave = None
        self.shutdown = False
        self.run_thread = None
        self.frame_rate = 10

    def start(self):
        self.slave = self.i2c_controller.get_slave(self.i2c_address)
        pctl_val = PCTL.NORMAL_MODE
        self.slave.write_reg_byte(PCTL.REGISTER, pctl_val)
        rst_val = RST.INITIAL_RESET
        self.slave.write_reg_byte(RST.REGISTER, rst_val)
        intc_val = INTC.INT_DISABLED | INTC.INT_MOD_DIFF
        self.slave.write_reg_byte(INTC.REGISTER, intc_val)
        fpsc_val = FPSC.FPS_10
        self.slave.write_reg_byte(FPSC.REGISTER, fpsc_val)
        time.sleep(0.5)
        
        ret_val = self.slave.read_reg_byte(PCTL.REGISTER)
        if pctl_val != ret_val:
            self.logger.warning("pctl_val expected:%s returned:%s", pctl_val, ret_val)
        #write only
        #ret_val = self.slave.read_reg_byte(RST.REGISTER)
        #if rst_val != ret_val:
        #    self.logger.warning("rst_val expected:%s returned:%s", rst_val, ret_val)
        ret_val = self.slave.read_reg_byte(INTC.REGISTER)
        if intc_val != ret_val:
            self.logger.warning("intc_val expected:%s returned:%s", intc_val, ret_val)
        ret_val = self.slave.read_reg_byte(FPSC.REGISTER)
        if fpsc_val != ret_val:
            self.logger.warning("fpsc_val expected:%s returned:%s", fpsc_val, ret_val)
        self.shutdown = False
        if not self.server is None:
            self.run_thread = threading.Thread(target=self.run, args=())
            self.run_thread.start()

    def run(self):
        self.logger.debug("running thread:%s", threading.current_thread().getName())
        try:
            self.main()
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("exception %s", ex)
        try:
            self.run_end()
        except Exception as ex:
            self.logger.debug("end exception %s", ex)
        self.logger.debug("terminated")

    def stop(self):
        if self.shutdown:
            self.logger.warning("Already stopped")
            return
        self.logger.debug("stopping")
        self.shutdown = True
        if self.run_thread is not None:
            self.logger.debug("join th:%s", self.run_thread.getName())
            self.run_thread.join()
        self.slave.close()

    def run_end(self):
        pass

    def main(self):
        frame_rate_delay = 1 / self.frame_rate
        last_frame_time = 0
        while not self.shutdown:
            if last_frame_time != 0:
                delay = time.time() - last_frame_time
                if delay < frame_rate_delay:
                    time.sleep(frame_rate_delay - delay)
            pixels = self.readPixels()
            #for px in range(64):
            #    pixels[px] = px
            data = (ctypes.c_float * len(pixels))()
            data[:] = pixels
            data = bytes(data)
            #64f
            fmt1 = "%sf" % len(pixels)
            fmt2 = f"{len(pixels)}f"
            fmt3 = "{}f".format(len(pixels))
            if fmt1!=fmt2 or fmt2!=fmt3:
                self.logger.error("fmt issue")
            data1 = struct.pack(fmt1, *pixels)
            if data1!=data:
                self.logger.error("serialization issues")
            width = 8
            height = 8
            self.server.send_data(width.to_bytes(2, "little"))
            self.server.send_data(height.to_bytes(2, "little"))
            data_len = len(data)
            self.server.send_data(data_len.to_bytes(2, "little"))
            self.server.send_data(data)
            last_frame_time = time.time()

    def readPixels(self):
        pixels = []
        for px in range (64):
            pixel = self.slave.write_read_data([REGISTER_MAP.PIXEL01_OUTPUT_L + (px<<1)], 2)
            raw = pixel[0] | (pixel[1] << 8)
            temp = float(raw - 4096*((pixel[1] & 8)>>3)) * 0.25
            pixels.append(temp)
        return pixels

    def readThermistor(self):
        lo = self.slave.read_reg_byte(REGISTER_MAP.T00L)
        hi = self.slave.read_reg_byte(REGISTER_MAP.T00H)
        raw = lo | (hi << 8)
        val = float(raw & 0x7FF) * 0.0625
        sign = (raw & 0x800) == 0x800
        return -val if sign else val

class GridEyeTcpServer(TcpServer.TcpServer):
    def __init__(self, address, log_level):
        super().__init__("GridEyeTcpServer", address, log_level)

if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting test")
    try:
        tcp_server = GridEyeTcpServer(('', 5555), logging.DEBUG)
        tcp_server.start()

        if sys.platform == "linux" or sys.platform == "linux2":
            import DeviceI2CController
            i2c_com = DeviceI2CController.DeviceI2CController(1, logging.INFO)
        else:
            import FakeI2CController
            i2c_com = FakeI2CController.FakeI2CController(logging.INFO)

        i2c_com.start()
        controller = GridEyeController(i2c_com, logging.DEBUG, tcp_server)
        controller.start()

        time.sleep(1)
        t = controller.readThermistor()
        print("Thermistor value={0}".format(t))

        input("===> Press Enter to quit...\n")
    except KeyboardInterrupt:
        print("*** Keyboard Interrupt ***")
    except Exception as ex:
        logging.fatal("Exception: %s", ex)

    controller.stop()
    tcp_server.stop()
