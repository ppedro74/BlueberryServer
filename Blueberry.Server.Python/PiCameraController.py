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
            data = bytearray()
            data += self.TAG_EZ_IMAGE
            img_len = stream.tell()
            data += img_len.to_bytes(4, "little")
            stream.seek(0)
            data += stream.read()
            self.server.send_image(bytes(data))
            stream.seek(0)
            stream.truncate()

    def run_end(self):
        self.camera.stop_preview()

