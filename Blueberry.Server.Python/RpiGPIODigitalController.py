import RPi.GPIO as GPIO
import DigitalController

class RpiGPIODigitalController(DigitalController.DigitalController):
    def __init__(self, log_level):
        super().__init__("RpiGPIODigitalController", log_level)
        self.directions = dict()
        GPIO.setmode(GPIO.BCM)

    def ensure_direction(self, port, is_output):
        if port not in self.directions:
            self.directions[port] = -1

        if (is_output):
            if self.directions[port] != 1:
                self.logger.debug("direction changed to output")
                self.directions[port] = 1
                GPIO.setup(port, GPIO.OUT)
        else:
            if self.directions[port] != 0:
                self.logger.debug("direction changed to input")
                self.directions[port] = 0
                GPIO.setup(port, GPIO.IN)

    def set(self, port, state):
        self.ensure_direction(port, 1)
        GPIO.output(port, GPIO.HIGH if state>=1 else GPIO.LOW)

    def get(self, port):
        self.ensure_direction(port, 0)
        return GPIO.input(port)


