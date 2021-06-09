import sys
import logging
import time
import io
import math
import struct
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from PIL import Image
import TcpClient

class HeatCameraTcpClient(TcpClient.TcpClient):
    def __init__(self, log_level):
        super().__init__("GridEyeTcpClient", log_level)

    def main(self):
        cv2.namedWindow("image", cv2.WINDOW_NORMAL)
        #low range of the sensor (this will be blue on the screen)
        MINTEMP = 20.
        #high range of the sensor (this will be red on the screen)
        MAXTEMP = 35.
        #how many color values we can have
        COLORDEPTH = 1024

        points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
        grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]

        while not self.shutdown:
            data = self.recv(2)
            if data is None:
                break
            width = int.from_bytes(data, "little")
            data = self.recv(2)
            if data is None:
                break
            height = int.from_bytes(data, "little")
            data = self.recv(2)
            if data is None:
                break
            data_len = int.from_bytes(data, "little")
            data = self.recv(data_len)
            if data is None:
                break
            fmt = "{}f".format(height * width)
            pixels = struct.unpack(fmt, data)
            self.process(width, height, pixels)
            
    def process(self, width, height, pixels):
        r_width = 320
        ratio = r_width / 32
        r_height = int(height * ratio)
        temps = np.array(pixels)
        temps = temps.reshape((height, width))
        image = cv2.normalize(temps, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8UC1)
        image = cv2.resize(image, (r_width, r_height), )
        #interpolation = cv2.INTER_LANCZOS4
        interpolation = cv2.INTER_CUBIC
        image = cv2.applyColorMap(image, cv2.COLORMAP_JET, interpolation)
        
        cv2.imshow("image", image)
        if cv2.waitKey(1) == ord("q"):
            self.shutdown = True



if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting test")

    try:
        
        client = HeatCameraTcpClient(logging.INFO)
        client.connect(('rpi-buster-4g.home',5555))
        
        input("===> Press Enter to quit...\n")

    except KeyboardInterrupt:
        print("*** Keyboard Interrupt ***")
    except Exception as ex:
        logging.fatal("Exception: %s", ex)

    client.stop()
    cv2.destroyAllWindows()
