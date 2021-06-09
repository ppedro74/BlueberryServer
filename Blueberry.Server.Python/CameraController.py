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
        self.frame_rate = framerate
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.shutdown = False
        self.run_thread = None

    def setup(self):
        return True

    def start(self):
        if not self.setup():
            self.shutdown = True
            return

        self.shutdown = False
        self.run_thread = threading.Thread(target=self.run, args=())
        self.run_thread.start()

    def stop(self):
        if self.shutdown:
            self.logger.warning("Already stopped")
            return

        self.logger.debug("stopping")
        self.shutdown = True
        if self.run_thread is not None:
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
        pass

    def send_image(self, img_bytes):
        data = bytearray()
        data += self.TAG_EZ_IMAGE
        img_len = len(img_bytes)
        data += img_len.to_bytes(4, "little")
        data += img_bytes
        self.server.send_data(bytes(data))