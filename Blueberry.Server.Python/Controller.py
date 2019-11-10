import logging

class Controller(object):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

    def start(self):
        pass

    def stop(self):
        pass
