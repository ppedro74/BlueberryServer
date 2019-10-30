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
    def __init__(self, server, resolution, framerate, log_level):
        super().__init__("PiCameraController", server, resolution, framerate, log_level)

        self.camera = picamera.PiCamera()
        (width, height) = self.resolution
        self.camera.resolution = (width, height)
        prev_framerate = self.camera.framerate
        self.camera.framerate  = framerate
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
            stream.seek(0)
            stream.truncate()

    def run_end(self):
        self.camera.stop_preview()

