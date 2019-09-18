import sys
import threading
import logging
import os
import datetime
import time
import socket
import UdpBroadcaster 
import TcpServer 
import ComponentRegistry
import Controller
import EZBTcpClient

class EZBTcpServerUdpBroadcaster(UdpBroadcaster.UdpBroadcaster):
    def __init__(self, server, delay, log_level):
        self.server = server
        super().__init__("EZBTcpServerUdpBroadcaster", 4242, delay, log_level)

    def get_message(self, hostname, addr):
        return "{}||{}-Server||{}||{}".format("EZ-B", hostname, addr, self.server.port)


class EZBTcpServer(TcpServer.TcpServer):
    def __init__(self, port, log_level):
        super().__init__("EZBTcpServer", port, log_level)

    def get_client_instance(self, connection, client_address):
        return EZBTcpClient.EZBTcpClient(self, connection, client_address)

def start(port):
    server = EZBTcpServer(port, logging.DEBUG)
    server.start()
    ComponentRegistry.ComponentRegistry.register_component(server.name, server)

    broadcaster = EZBTcpServerUdpBroadcaster(server, 3, logging.DEBUG)
    broadcaster.start()
    ComponentRegistry.ComponentRegistry.register_component(broadcaster.name, broadcaster)



