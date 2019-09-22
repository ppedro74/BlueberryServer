"""
Copyright (c) 2019 Pedro Pereira

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import sys
import time
import socket
import logging
import Controller
import DigitalController
import PWMController
import ServoController
import SerialPortController
import ComponentRegistry
import EZBTcpServer
import EZBCameraServer

def setup_i2c():
    if sys.platform == "linux" or sys.platform == "linux2":
        import DeviceI2CController
        com = DeviceI2CController.DeviceI2CController(1, logging.DEBUG)
    else:
        import FakeI2CController
        com = FakeI2CController.FakeI2CController(logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_component("i2c", com)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    com.start()
    return com

def setup_digital_ports():
    if sys.platform == "linux" or sys.platform == "linux2":
        import RpiGPIODigitalController
        com = RpiGPIODigitalController.RpiGPIODigitalController(logging.DEBUG)
        ComponentRegistry.ComponentRegistry.register_controller(com)
        #+-----+---------+--B Plus--+-----------+-----+
        #| BCM |   Name  | Physical | Name      | BCM |
        #+-----+---------+----++----+-----------+-----+
        #|     |    3.3v |  1 || 2  | 5v        |     |
        #|   2 |   SDA.1 |  3 || 4  | 5v        |     |
        #|   3 |   SCL.1 |  5 || 6  | GND       |     |
        #|   4 |         |  7 || 8  | TxD       | 14  |
        #|     |     GND |  9 || 10 | RxD       | 15  |
        #|  17 |   CE1.1 | 11 || 12 | CE0.1/BCLK| 18  |
        #|  27 |         | 13 || 14 | GND       |     |
        #|  22 |         | 15 || 16 |           | 23  |
        #|     |    3.3v | 17 || 18 |           | 24  |
        #|  10 |    MO.0 | 19 || 20 | GND       |     |
        #|   9 |    MI.0 | 21 || 22 |           | 25  |
        #|  11 |   CLK.0 | 23 || 24 | CE0.0     | 8   |
        #|     |     GND | 25 || 26 | CE1.0     | 7   |
        #|   0 |   SDA.0 | 27 || 28 | SCL.0     | 1   |
        #|   5 |         | 29 || 30 | GND       |     |
        #|   6 |         | 31 || 32 |           | 12  |
        #|  13 |         | 33 || 34 | GND       |     |
        #|  19 |LRCK/MI.1| 35 || 36 | CE2.1     | 16  |
        #|  26 |         | 37 || 38 | MO.1/SDI  | 20  |
        #|     |     GND | 39 || 40 | CLK.1/SDO | 21  |
        #+-----+---------+----++----+-----------+-----+
        #| BCM |   Name  | Physical | Name      | BCM |
        #+-----+---------+--B Plus--+-----------+-----+
        #Generic pins (excluded: uart, i2c, spi, i2s):
        ComponentRegistry.ComponentRegistry.register_component("D4",  DigitalController.DigitalPort(com, 4))
        ComponentRegistry.ComponentRegistry.register_component("D5",  DigitalController.DigitalPort(com, 5))
        ComponentRegistry.ComponentRegistry.register_component("D6",  DigitalController.DigitalPort(com, 6))
        ComponentRegistry.ComponentRegistry.register_component("D12",  DigitalController.DigitalPort(com, 12))
        ComponentRegistry.ComponentRegistry.register_component("D13",  DigitalController.DigitalPort(com, 13))
        ComponentRegistry.ComponentRegistry.register_component("D22",  DigitalController.DigitalPort(com, 22))
        ComponentRegistry.ComponentRegistry.register_component("D23",  DigitalController.DigitalPort(com, 23))
        #Remapped 
        ComponentRegistry.ComponentRegistry.register_component("D0",  DigitalController.DigitalPort(com, 24))
        ComponentRegistry.ComponentRegistry.register_component("D1",  DigitalController.DigitalPort(com, 25))
        ComponentRegistry.ComponentRegistry.register_component("D2",  DigitalController.DigitalPort(com, 26))
        ComponentRegistry.ComponentRegistry.register_component("D3",  DigitalController.DigitalPort(com, 27))
        com.start()
    else:
        import FakeDigitalController
        com = FakeDigitalController.FakeDigitalController(logging.DEBUG)
        ComponentRegistry.ComponentRegistry.register_controller(com)
        for port in range(24):
            ComponentRegistry.ComponentRegistry.register_component("D" + str(port),  DigitalController.DigitalPort(com, port))
        com.start()

def setup_i2c_PCA9685Controller(i2c_com, freq=490):
    import PCA9685Controller
    com = PCA9685Controller.PCA9685Controller(i2c_com, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    for port in range(16):
        ComponentRegistry.ComponentRegistry.register_component("P"+str(port), PWMController.PWMPort(com, port))
    com.start()
    com.frequency = freq

def setup_i2c_PCA9685ServoController(i2c_com):
    import PCA9685Controller
    com = PCA9685Controller.PCA9685ServoController(i2c_com, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    for port in range(16):
        ComponentRegistry.ComponentRegistry.register_component("S"+str(port), ServoController.ServoPort(com, port, 560, 2140))
    #bear in mind pwm ports frequency is 50 hz used for servos (frequency is per controller) 
    for port in range(16):
        ComponentRegistry.ComponentRegistry.register_component("P"+str(port), PWMController.PWMPort(com, port))
    com.start()

def setup_i2c_PimoroniPanTiltHatServoController(i2c_com):
    import PimoroniPanTiltHatServoController
    com = PimoroniPanTiltHatServoController.PimoroniPanTiltHatServoController(i2c_com, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    for port in range(2):
        ComponentRegistry.ComponentRegistry.register_component("S"+str(port), ServoController.ServoPort(com, port, 575, 2325))    
    com.start()

def setup_serial_MaestroServoController(serial_port_name):
    import MaestroServoController
    com = MaestroServoController.MaestroServoController(serial_port_name, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    for port in range(24):
        #ez-robot servos: 560-2140 us
        ComponentRegistry.ComponentRegistry.register_component("S"+str(port), ServoController.ServoPort(com, port, 560, 2140))
    com.start()

def setup_SerialPortController(component_name, device_name, baud_rate):
    com = SerialPortController.SerialPortController(device_name, baud_rate, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_component(component_name, com)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    com.start()

def setup_PyAudioPlayerController():
    os.environ["PA_ALSA_PLUGHW"] = "1"
    import PyAudioPlayerController
    com = PyAudioPlayerController.PyAudioPlayerController(logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_component("audio_player", com)
    ComponentRegistry.ComponentRegistry.register_controller(com)
    com.start()
   

def main():
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting... platform=%s hostname=%s", sys.platform, socket.gethostname())

    #audio support
    #setup_PyAudioPlayerController()

    setup_digital_ports()

    i2c_com = setup_i2c()
    
    #setup_SerialPortController("uart0", "/dev/serial0" if sys.platform == "linux" or sys.platform == "linux2" else "com40", 115200)


    ###Pololu Mini Maestro 24-Channel USB Servo Controller https://www.pololu.com/product/1356
    ###Used for 24 servos ports D0..D23
    #setup_serial_MaestroServoController("/dev/ttyACM0" if sys.platform == "linux" or sys.platform == "linux2" else "com40")

    ###Adafruit 16-Channel PWM https://www.adafruit.com/product/2327 
    ###Used for PWM ports (0..23)
    #setup_i2c_PCA9685Controller(i2c_com)
    ###Used for Servo ports (0..23)
    #setup_i2c_PCA9685ServoController(i2c_com)

    ###Pimoroni Pan-Tilt HAT  https://shop.pimoroni.com/products/pan-tilt-hat
    ###Used to map servo ports D0..D1
    #setup_i2c_PimoroniPanTiltHatServoController(i2c_com)


    EZBTcpServer.start(10023)
    EZBCameraServer.start(10024)

    time.sleep(3)
    input("===> Press Enter to quit...\n")

    logging.debug("*** Enter pressed ***")

    controllers = ComponentRegistry.ComponentRegistry.Controllers.copy()
    controllers.reverse()
    for controller in controllers:
        logging.info("stopping controller: %s", controller.name)
        controller.stop()

    logging.info("Terminated")


if __name__ == "__main__":
    main()

