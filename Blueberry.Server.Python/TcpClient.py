import sys
import threading
import logging
import os
import datetime
import time
import socket
import traceback

class TcpClient:

    def __init__(self, name, log_level, client_address=None, client_socket=None, server=None):
        self.name = "{}-{}".format(name, client_address)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(log_level)
        self.address = client_address
        self.socket = client_socket
        self.server = server
        self.all_data = bytearray() 
        self.shutdown = False
        if self.server is not None:
            self.run_thread = threading.Thread(target=self.run, args=())
            self.run_thread.start()

    def connect(self, server_address):
        self.server_address = server_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(server_address)
        self.run_thread = threading.Thread(target=self.run, args=())
        self.run_thread.start()

    def stop(self):
        self.logger.debug("stopping client:%s ...", self.address)
        self.shutdown = True
        self.logger.debug("join th:%s", self.run_thread.getName())
        if self.run_thread is not None:
            self.run_thread.join()

    def recv(self, req_size):
        try:
            seq = 0
            while not self.shutdown:
                if req_size<=len(self.all_data):
                    data = self.all_data[:req_size]
                    self.all_data = self.all_data[req_size:]
                    return bytes(data)
                try:
                    data = self.socket.recv(10240)
                except socket.timeout as ex:
                    continue

                if data is None or data == b"":
                    return None
                self.all_data += data
                self.logger.debug("recv seq=%s len=%s len2=%s", seq, len(data), len(self.all_data))
                seq += 1
        except socket.error as ex:
            self.logger.error("recv ex=%s", ex)
        return None
    
    def main(self):
        while not self.shutdown:
            try:
                data = self.socket.recv(1024)
            except socket.timeout as ex:
                continue

            if data is None or data==b"":
                break
            
            self.logger.debug("run: data %s", data)

    def run(self):
        self.logger.debug("running thread:%s", threading.current_thread().getName())
    
        try:
            self.socket.settimeout(2)
            self.main()
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("exception %s", ex)
            traceback.print_exc()

        self.logger.debug("shutting down....")
        if self.server is not None:
            self.server.unregister_client(self)
        self.socket.close()
        self.logger.debug("terminated")
    
    def send(self, data):
        try:
            self.socket.send(data)
        except Exception as ex:
            self.logger.debug("send exception %s", ex)


