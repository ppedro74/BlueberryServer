import sys
import logging
import Maestro
import ServoController

class MaestroServoController(ServoController.ServoController):
    def __init__(self, serial_port_name, log_level):
        super().__init__("MaestroServoController", log_level)
        self.serial_port_name = serial_port_name
        self.controller = None

    def release(self, port):
        self.logger.debug("release port=%s", port)
        self.controller.setTarget(port, 0) 

    def set_position(self, port, position_in_us):
        #convert to quarter-microseconds
        self.logger.debug("set_position port=%s position_in_us=%s", port, position_in_us)
        self.controller.setTarget(port, position_in_us * 4) 

    def set_speed(self, port, speed):
        if speed>0:
            #ezb => 1-10(slowest)
            #maestro 1(slowest)
            #10 ezb = 2 maestro
            speed = 12-speed
        self.logger.debug("set_speed port=%s speed=%s", port, speed)
        self.controller.setSpeed(port, speed) 

    def start(self):
        self.controller = Maestro.Controller(self.serial_port_name)

    def stop(self):
        self.controller.close()

def test():
    logging.basicConfig(format="%(process)d-%(levelname)s-%(message)s", level=logging.DEBUG)
    logging.info("Starting... platform=%s", sys.platform)

    controller = Maestro.Controller("com40")
    #controller.setAccel(0,4) #set servo 0 acceleration to 4
    #controller.setSpeed(1,10) #set speed of servo 1
    controller.setTarget(0, 1000 * 4)  #set servo to move to center position
    #controller.setTarget(1, 1000 * 4)  #set servo to move to center position
    #controller.setTarget(2, 1000 * 4)  #set servo to move to center position
    #x = controller.getPosition(1)      #get the current position of servo 1

    input("Press Enter to continue...")
    
    controller.close()

if __name__ == "__main__":
    test()