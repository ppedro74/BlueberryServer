import logging
import Controller

class DigitalPort:
    def __init__(self, digital_port_controller, port):
        self.digital_port_controller = digital_port_controller
        self.port = port
        self.logger = logging.getLogger("{}-{}".format(digital_port_controller.name, port))
        self.logger.setLevel(digital_port_controller.log_level)

    def set(self, state):
        self.digital_port_controller.set(self.port, state)

    def get(self):
        return self.digital_port_controller.get(self.port)

class DigitalController(Controller.Controller):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(log_level)

    def set(self, port, state):
        pass

    def get(self, port):
        return 0



