import logging
import Controller

class AudioPlayerController(Controller.Controller):
    def __init__(self, name, log_level):
        self.name = name
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
    
    def stop(self):
        pass

    def start(self):
        pass

    def stream_init(self):
        pass

    def stream_stop(self):
        pass

    def stream_load(self, data):
        pass

    def stream_play(self):
        pass

