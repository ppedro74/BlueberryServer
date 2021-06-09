import sys
import threading
import logging
import os
import io
import datetime
import time
import socket
import TcpClient
import TcpServer
import UdpBroadcaster
import ComponentRegistry

class EZBCameraUdpBroadcaster(UdpBroadcaster.UdpBroadcaster):
    def __init__(self, server, delay, log_level):
        self.server = server
        super().__init__("EZBCameraUdpBroadcaster", 4242, delay, log_level)

    def get_message(self, hostname, addr):
        return "{}||{}-Server||{}||{}".format("Camera", hostname, addr, self.server.address[1])

class EZBCameraTcpClient(TcpClient.TcpClient):
    def __init__(self, log_level, address, client_socket, server):
        super().__init__("EZBCameraTcpClient", log_level, address, client_socket, server)

class EZBCameraTcpServer(TcpServer.TcpServer):
    def __init__(self, address, log_level):
        super().__init__("EZBCameraTcpServer", address, log_level)

    def get_client_instance(self, connection, address):
        return EZBCameraTcpClient(self.log_level, address, connection, self)

    def send_image(self, data):
        clients = self.clients.copy()
        for client in clients: 
            client.send(data)

def start(addr, args):
    server = EZBCameraTcpServer(addr, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_controller(server)

    broadcaster = EZBCameraUdpBroadcaster(server, 3, logging.DEBUG)
    broadcaster.start()
    ComponentRegistry.ComponentRegistry.register_controller(broadcaster)

    camera = None

    if args.camtype == "videocapture":
        import OCVCamera
        camera = OCVCamera.OCVCameraController(server, (args.camwidth, args.camheight), args.camfps, logging.DEBUG, args.videocaptureindex, args.jpgquality)
        camera.start()
        ComponentRegistry.ComponentRegistry.register_controller(camera)
    elif args.camtype == "picamera":
        import PiCameraController
        camera = PiCameraController.PiCameraController(server, (args.camwidth, args.camheight), args.camfps, args.camrotation, args.camflip, logging.DEBUG)
        camera.start()
        ComponentRegistry.ComponentRegistry.register_controller(camera)
    elif args.camtype == "fake":
        import FakeCameraController
        camera = FakeCameraController.FakeCameraController(server, (args.camwidth, args.camheight), args.camfps, logging.DEBUG)
        camera.start()
        ComponentRegistry.ComponentRegistry.register_controller(camera)

    #time.sleep(3)
    server.start()
    return True

def stop():
    broadcaster.stop()
    camera.stop()
    server.stop()

def main():
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.DEBUG)
    logging.info("Starting Camera Server... platform=%s hostname=%s", sys.platform, socket.gethostname())
    start(10024)
    input("===> Press Enter to quit...\n")
    logging.debug("*** Enter pressed ***")
    stop()
    logging.info("Terminated")

if __name__ == "__main__":
    main()

