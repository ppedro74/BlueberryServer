import logging
import Controller

class PWMPort:
    def __init__(self, pwm_controller, port):
        self.pwm_controller = pwm_controller
        self.port = port
        self.logger = logging.getLogger("{}-{}".format(pwm_controller.name, port))
        self.logger.setLevel(pwm_controller.log_level)

    def set_duty_cycle(self, percent):
        self.pwm_controller.set_duty_cycle(self.port, percent)

class PWMController(Controller.Controller):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(log_level)

    def set_duty_cycle(self, port, percent):
        pass






