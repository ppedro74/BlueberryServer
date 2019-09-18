import sys
import threading
import logging
import os
import io
import datetime
import time
import CameraController
import PIL.Image
import PIL.ImageDraw

class FakeCameraController(CameraController.CameraController):
    def __init__(self, server, resolution, framerate, log_level):
        super().__init__("FakeCameraController", server, resolution, framerate, log_level)
        self.frame_rate_delay = 1 / framerate

    def main(self):
        frame = 0
        while not self.shutdown:
            (width, height) = self.resolution
            img = PIL.Image.new("RGB", self.resolution, color = (73, 109, 137))
            draw = PIL.ImageDraw.Draw(img)
            draw.text((10,10), "Frame: {}".format(frame), fill=(255,255,0))
            frame += 1
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="JPEG", quality=100, subsampling=0)
            data = bytearray()
            data += self.TAG_EZ_IMAGE
            img_bytes = img_buffer.getvalue() 
            img_len = len(img_bytes)
            data += img_len.to_bytes(4, "little")
            data += img_bytes
            self.server.send_image(bytes(data))
            time.sleep(self.frame_rate_delay)
