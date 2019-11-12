import sys
import threading
import logging
import os
import datetime
import time
import socket
import Controller
import UdpBroadcaster
import TcpClient

class TcpServer(Controller.Controller):
    def __init__(self, name, address, log_level):
        self.name = name
        self.address = address
        self.log_level = log_level
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(2.0)
        self.shutdown = False
        self.lock = threading.Lock()
        self.clients = []
        self.run_thread = None

    def get_client_instance(self, connection, client_address):
        return TcpClient.TcpClient("TcpClient", self, connection, client_address)

    def run(self):
        try:
            last_debug_dt = None
            while not self.shutdown:
                try:
                    ds = 1917 if last_debug_dt is None else (datetime.datetime.now()-last_debug_dt).total_seconds()
                    if ds>=60: 
                        self.logger.debug("waiting for a connection")
                        last_debug_dt = datetime.datetime.now()

                    connection, client_address = self.socket.accept()
                    self.logger.info("accepted client connection from %s", client_address)

                    client = self.get_client_instance(connection, client_address)
                    self.register_client(client)
                except socket.timeout as e:
                    pass
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("exception ex=%s", ex)

        self.logger.debug("shutting down....")
        self.shutdown = True
        self.socket.close()
        self.logger.debug("terminated")

    def start(self):
        self.logger.debug("starting up on %s", self.address)

        try:
            self.socket.bind(self.address)
            self.socket.listen(1)

            self.run_thread = threading.Thread(target=self.run,args=())
            self.run_thread.start()
        except socket.error as ex:
            self.shutdown = True
            self.logger.error("start ex=%s", ex)

    def stop(self):        
        self.logger.debug("stopping....")
        self.shutdown = True

        if not self.run_thread is None:
            self.logger.debug("join th:%s run_thread", self.run_thread.getName())
            self.run_thread.join()

        clients = self.clients.copy()
        for client in clients: 
            client.stop()

        self.logger.debug("stopped")

    def register_client(self, client):
        self.lock.acquire()
        try:
            self.clients.append(client)
            self.logger.debug("register client:%s #clients:%s", client.client_address, len(self.clients))
        finally:
            self.lock.release()

    def unregister_client(self, client):
        self.lock.acquire()
        try:
            if client in self.clients:
                self.clients.remove(client)
                self.logger.debug("unregister client:%s #clients:%s", client.client_address, len(self.clients))
        finally:
            self.lock.release()

    def send_image(self, data):
        clients = self.clients.copy()
        for client in clients: 
            client.send(data)
