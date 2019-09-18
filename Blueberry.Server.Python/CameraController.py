import sys
import threading
import logging
import os
import io
import datetime
import time
import socket
import Controller

class CameraController(Controller.Controller):
    TAG_EZ_IMAGE = bytearray(b"EZIMG") 

    def __init__(self, name, server, resolution, framerate, log_level):
        self.name = name
        self.server = server
        self.resolution = resolution
        self.framerate = framerate
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.shutdown = False

    def start(self):
        self.shutdown = False
        self.run_thread = threading.Thread(target=self.run, args=())
        self.run_thread.start()

    def stop(self):
        if self.shutdown:
            self.logger.warning("Already stopped")
            return

        self.logger.debug("stopping")
        self.shutdown = True
        self.logger.debug("join th:%s", self.run_thread.getName())
        self.run_thread.join()

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
    
    def run_end(self):
        pass

    def main(self):
        frame_rate_delay = 1 / self.framerate
        while not self.shutdown:
            data = bytearray()
            data += self.TAG_EZ_IMAGE
            img_len = 0
            data += img_len.to_bytes(4, "little")
            stream.seek(0)
            data += bytearray()
            self.server.send_image(bytes(data))
