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
    def __init__(self, server, client_socket, client_address):
        super().__init__("EZBCameraTcpClient", server, client_socket, client_address)

class EZBCameraTcpServer(TcpServer.TcpServer):
    def __init__(self, address, log_level):
        super().__init__("EZBCameraTcpServer", address, log_level)

    def get_client_instance(self, connection, client_address):
        return EZBCameraTcpClient(self, connection, client_address)

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
        try:
            import OCVCamera
            camera = OCVCamera.OCVCameraController(server, (args.camwidth, args.camheight), args.camfps, logging.DEBUG, args.videocaptureindex, args.jpgquality)
            camera.start()
            ComponentRegistry.ComponentRegistry.register_controller(camera)
        except Exception as ex:
            logging.error("Error loading OCVCameraController ex=%s", ex)
    elif args.camtype == "picamera":
        try:
            import PiCameraController
            camera = PiCameraController.PiCameraController(server, (args.camwidth, args.camheight), args.camfps, args.camrotation, args.camflip, logging.DEBUG)
            camera.start()
            ComponentRegistry.ComponentRegistry.register_controller(camera)
        except Exception as ex:
            logging.error("Error loading PiCameraController ex=%s", ex)
            
    if camera is None:
        import FakeCameraController
        camera = FakeCameraController.FakeCameraController(server, (args.camwidth, args.camheight), args.camfps, logging.DEBUG)
        camera.start()
        ComponentRegistry.ComponentRegistry.register_controller(camera)

    time.sleep(3)

    server.start()

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

