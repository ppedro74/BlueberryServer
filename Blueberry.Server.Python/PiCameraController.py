import sys
import threading
import logging
import os
import io
import datetime
import time
import picamera
import CameraController

class PiCameraController(CameraController.CameraController):
    def __init__(self, server, resolution, framerate, rotation, flip, log_level):
        super().__init__("PiCameraController", server, resolution, framerate, log_level)

        self.camera = picamera.PiCamera()
        (width, height) = self.resolution
        self.camera.resolution = (width, height)
        prev_framerate = self.camera.framerate
        self.camera.framerate  = framerate
        self.camera.rotation = rotation
        if flip == "horizontal" or flip == "both":
            self.camera.hflip = True
        if flip == "vertical" or flip == "both":
            self.camera.vflip = True
        self.logger.debug("framerate previous=%s current=%s", prev_framerate, self.camera.framerate)

    def main(self):
        self.camera.start_preview()
        time.sleep(2)
        stream = io.BytesIO()
        for foo in self.camera.capture_continuous(stream, "jpeg", use_video_port=True):
            if self.shutdown:
                break
            stream.seek(0)
            img_bytes = bytes(stream.read())
            self.send_image(img_bytes)
            if img_bytes[0] != 255 or img_bytes[1] != 216:
                self.logger.warning("JPG's SOI missing")
            if img_bytes[-2] != 255 or img_bytes[-1] != 217:
                self.logger.warning("JPG's EOI missing")
            stream.seek(0)
            stream.truncate()

    def run_end(self):
        self.camera.stop_preview()

