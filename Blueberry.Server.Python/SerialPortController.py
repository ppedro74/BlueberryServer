import sys
import threading
import logging
import os
import datetime
import time
import serial
import serial.tools.list_ports
import Controller

class SerialPortController(Controller.Controller):
    DEBUG_INTERVAL = 5 * 60 # 5 minutes

    def __init__(self, port, baud_rate, log_level):
        self.port = port
        self.baud_rate = baud_rate
        self.name = "dev-{}".format(port)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(log_level)
        self.lock = threading.Lock()
        self.shutdown = True
        self.serial = None
        self.all_data = bytearray()
        self.total_bytes_read = 0
        self.is_data_ready = threading.Event()
        self.is_data_ready.clear()

    def start(self):
        self.logger.debug("Starting...")
        self.shutdown = False
        try:
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=0)
            self.run_thread = threading.Thread(target=self.run,args=())
            self.run_thread.start()
        except:
            self.shutdown = True
            raise
        return

    def stop(self):
        if self.shutdown:
            self.logger.warning("Already stopped")
            return

        self.shutdown = True
        self.run_thread.join()

    def run(self):
        self.logger.debug("started")
        try:
            last_debug_dt = None

            while not self.shutdown:
                if self.serial.isOpen():
                    if self.serial.inWaiting()>0:
                        data = self.serial.read(self.serial.inWaiting())

                        self.lock.acquire()
                        try:
                            self.all_data += data
                            self.total_bytes_read += len(data)
                            self.is_data_ready.set()
                        finally:
                            self.lock.release()

                        time.sleep(0.1) # Wait 100ms
                else:
                    time.sleep(1) # Wait 1s

                ds = 1917 if last_debug_dt is None else (datetime.datetime.now()-last_debug_dt).total_seconds()
                if ds>=self.DEBUG_INTERVAL:
                    self.logger.debug("run isOpen:%s available_bytes:%s total_bytes_read:%s", self.serial.isOpen(), self.get_available_bytes(), self.total_bytes_read)
                    last_debug_dt = datetime.datetime.now()
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("run exception ex=%s", ex)

        self.is_data_ready.set()
        self.serial.close()

        self.logger.debug("terminated")

    def write(self, data):
        if self.serial.isOpen():
            self.serial.write(data)

    def read(self, bytes_to_read, fill_zeros_if_missing = True):
        missing = 0
        self.lock.acquire()
        try:
            if len(self.all_data)>=bytes_to_read:
                data = self.all_data[:bytes_to_read]
                self.all_data = self.all_data[bytes_to_read:]
            else:
                data = self.all_data
                self.all_data = bytearray()
                if fill_zeros_if_missing:
                    missing = bytes_to_read - len(data)
                    data += bytes([0] * missing)

            if len(self.all_data)>0 or self.shutdown:
                self.is_data_ready.set()
            else:
                self.is_data_ready.clear()
        finally:
            self.lock.release()
        if missing:        
            self.logger.warning("read bytes_to_read:%s missing:%s", bytes_to_read, missing)
        return bytes(data)

    def get_available_bytes(self):
        self.lock.acquire()
        try:
            return len(self.all_data)
        finally:
            self.lock.release()

    def clear_buffer(self):
        self.lock.acquire()
        try:
            self.all_data = bytearray()
        finally:
            self.lock.release()

    def list_ports():
        logging.debug("Available serial ports:")
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            logging.debug("...port:%s desc:%s hwid:%s", port, desc, hwid)

if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.DEBUG)

    SerialPortController.list_ports()