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
        return "{}||{}-Server||{}||{}".format("EZ-B", hostname, addr, self.server.address[1])


class EZBTcpServer(TcpServer.TcpServer):
    def __init__(self, address, log_level):
        super().__init__("EZBTcpServer", address, log_level)

    def get_client_instance(self, connection, address):
        return EZBTcpClient.EZBTcpClient(address, connection, self)

def start(addr):
    server = EZBTcpServer(addr, logging.DEBUG)
    server.start()
    ComponentRegistry.ComponentRegistry.register_controller(server)

    broadcaster = EZBTcpServerUdpBroadcaster(server, 3, logging.DEBUG)
    broadcaster.start()
    ComponentRegistry.ComponentRegistry.register_controller(broadcaster)



