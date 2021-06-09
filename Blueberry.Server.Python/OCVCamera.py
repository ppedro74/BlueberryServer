import threading
import logging
import time
import cv2
import CameraController

class OCVCameraController(CameraController.CameraController):

    def __init__(self, server, resolution, framerate, log_level, device_index=0, quality=95):
        super().__init__(self.__class__.__name__ + "-" + str(device_index), server, resolution, framerate, log_level)
        self.device_index = device_index
        self.quality = quality

    def setup(self):
        self.logger.debug("opening videocapture device=%s", self.device_index)
        self._video_capture = cv2.VideoCapture(self.device_index)
        if not self._video_capture.isOpened():
            self.logger.error("can't open video device:%s", self.device_index)
            return False

        w = self._video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self._video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        f = self._video_capture.get(cv2.CAP_PROP_FPS)
        self.logger.debug("current width=%s height=%s fps=%s", w, h, f)

        self._video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self._video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self._video_capture.set(cv2.CAP_PROP_FPS, self.frame_rate)
        w = self._video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self._video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        f = self._video_capture.get(cv2.CAP_PROP_FPS)
        self.logger.debug("requested width=%s height=%s fps=%s", w, h, f)

        if w!=self.resolution[0] or h!=self.resolution[1]:
            self.logger.error("video device:%s invalid resolution requested=% current=%s", 
                              self.device_index,
                              self.resolution,
                              (w,h))
            self._video_capture.release()
            return False

        if f!=self.frame_rate:
            self.logger.warning("fps setting ignored requested=%s current=%s", self.frame_rate, f)
        
        self.logger.debug("setup finished")
        return True

    def run_end(self):
        self._video_capture.release()
        return

    def main(self):
        frame_rate_delay = 1.0 / self.frame_rate
        last_frame_time = 0
        while not self.shutdown:
            if last_frame_time != 0:
                delay = time.time() - last_frame_time
                if delay < frame_rate_delay:
                    time.sleep(frame_rate_delay - delay)

            ret, frame = self._video_capture.read()
            if ret:
                ret, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                if ret:
                    jpg_bytes = jpg.tobytes()
                    self.send_image(jpg_bytes)
                else:
                    self.logger.warning("no jpg")
            else:
                self.logger.warning("no frame")

            last_frame_time = time.time()
        return
        

