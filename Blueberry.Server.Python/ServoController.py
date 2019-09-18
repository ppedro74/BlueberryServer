import logging
import Controller

class ServoPort:
    def __init__(self, servo_controller, port, min_us, max_us, min_degrees=0, max_degrees=179):
        self.servo_controller = servo_controller
        self.port = port
        self.min_us = min_us
        self.max_us = max_us
        self.min_degrees = min_degrees
        self.max_degrees = max_degrees
        self.logger = logging.getLogger("{}-{}".format(servo_controller.name, port))
        self.logger.setLevel(servo_controller.log_level)

    def set_position(self, position_in_degrees):
        position_in_us = self.degrees_to_us(position_in_degrees)
        if position_in_us>self.max_us:
            position_in_us = self.max_us
        elif position_in_us<self.min_us:
            position_in_us = self.min_us
        self.servo_controller.set_position(self.port, position_in_us)

    def set_speed(self, speed):
        self.servo_controller.set_speed(self.port, speed)

    def degrees_to_us(self, degrees):
        # Figure out how 'wide' each range is
        degrees_span = self.max_degrees - self.min_degrees
        us_span = self.max_us - self.min_us

        # Convert the left range into a 0-1 range (float)
        degrees_scaled = float(degrees - self.min_degrees) / float(degrees_span)

        # Convert the 0-1 range into a value in the right range.
        us = int(self.min_us + (degrees_scaled * us_span))
        return us

    def release(self):
        self.servo_controller.release(self.port)

class ServoController(Controller.Controller):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

    def set_position(self, port, position_in_us):
        pass

    def set_speed(self, port, speed):
        pass

    def release(self, port):
        pass

    def start(self):
        pass

    def stop(self):
        pass
