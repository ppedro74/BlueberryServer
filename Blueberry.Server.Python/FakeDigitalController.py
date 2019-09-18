import DigitalController

class FakeDigitalController(DigitalController.DigitalController):
    def __init__(self, log_level):
        super().__init__("FakeDigitalController", log_level)
        self.directions = dict()

    def ensure_direction(self, port, is_output):
        if port not in self.directions:
            self.directions[port] = -1

        if (is_output):
            if self.directions[port] != 1:
                self.logger.debug("direction changed to output")
                self.directions[port] = 1
        else:
            if self.directions[port] != 0:
                self.logger.debug("direction changed to input")
                self.directions[port] = 0

    def set(self, port, state):
        self.logger.debug("set port=%s state=%s", port, state)
        self.ensure_direction(port, 1)

    def get(self, port):
        fake_state = 0
        self.ensure_direction(port, fake_state)
        self.logger.debug("get port=%s => state=%s", port, fake_state)        
        return 0


