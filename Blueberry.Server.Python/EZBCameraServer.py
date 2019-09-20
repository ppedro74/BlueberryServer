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
        return "{}||{}-Server||{}||{}".format("Camera", hostname, addr, self.server.port)

class EZBCameraTcpClient(TcpClient.TcpClient):
    def __init__(self, server, client_socket, client_address):
        super().__init__("EZBCameraTcpClient", server, client_socket, client_address)

class EZBCameraTcpServer(TcpServer.TcpServer):
    def __init__(self, port, log_level):
        super().__init__("EZBCameraTcpServer", port, log_level)

    def get_client_instance(self, connection, client_address):
        return EZBCameraTcpClient(self, connection, client_address)

    def send_image(self, data):
        clients = self.clients.copy()
        for client in clients: 
            client.send(data)

def start(port):
    server = EZBCameraTcpServer(port, logging.DEBUG)
    ComponentRegistry.ComponentRegistry.register_component(server.name, server)

    broadcaster = EZBCameraUdpBroadcaster(server, 3, logging.DEBUG)
    broadcaster.start()
    ComponentRegistry.ComponentRegistry.register_component(broadcaster.name, broadcaster)

    use_fake_camera = True
    
    if sys.platform == "linux" or sys.platform == "linux2":
        try:
            import PiCameraController
            camera = PiCameraController.PiCameraController(server, (320,240), 30, logging.DEBUG)
            camera.start()
            ComponentRegistry.ComponentRegistry.register_component(camera.name, camera)
            use_fake_camera = False
        except Exception as ex:
            logging.error("Error loading PiCameraController ex=%s", ex)
            
    if use_fake_camera:
        import FakeCameraController
        camera = FakeCameraController.FakeCameraController(server, (320,240), 32, logging.DEBUG)
        camera.start()
        ComponentRegistry.ComponentRegistry.register_component(camera.name, camera)

    time.sleep(3)
    server.start()

def stop():
    broadcaster.stop()
    camera.stop()
    server.stop()

def main():
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.INFO)
    logging.info("Starting Camera Server... platform=%s hostname=%s", sys.platform, socket.gethostname())
    start(10024)
    input("===> Press Enter to quit...\n")
    logging.debug("*** Enter pressed ***")
    stop()
    logging.info("Terminated")

if __name__ == "__main__":
    main()

