import sys
import threading
import logging
import os
import datetime
import time
import socket
import SerialPortController


class TcpSerialPortClient:

    def __init__(self, server, client_socket, address):
        self.logger = logging.getLogger("TcpSerialPortClient-{}".format(address))
        self.server = server
        self.socket = client_socket
        self.address = address
        self.run_thread = threading.Thread(target=self.run, args=())
        self.run_thread.start()

    def run(self):
        self.logger.debug("running thread:%s", threading.current_thread().getName())
    
        try:
            while not self.server.shutdown:
                data = self.socket.recv(1024)
                if data is None or data == b"":
                    break
                self.server.serial_port_component.write(data)

        except Exception as e:
            self.logger.debug("run exception %s", e)

        self.logger.debug("shutting down....")
        self.socket.close()
        self.server.unregister_client(self)
        self.logger.debug("terminated")

    def stop(self):
        self.logger.debug("stopping client:%s ...", self.address)
        self.socket.close()

    def send(self, data):
        try:
            self.socket.sendall(data)
        except Exception as e:
            self.logger.debug("send ex:%s", e)

class TcpSerialPortBridge(object):
    def __init__(self, port, serial_port_component):
        self.logger = logging.getLogger("TcpSerialPortBridge")
        self.port = port
        self.serial_port_component = serial_port_component
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(2.0)
        self.shutdown = False
        self.lock = threading.Lock()
        self.clients = []

    def run_serial(self):
        self.logger.debug("run_serial started")
        try:
            while not self.shutdown:
                if self.serial_port_component.is_data_ready.isSet():
                    if self.shutdown:
                        break
                    data_len = self.serial_port_component.get_available_bytes()
                    data = self.serial_port_component.read(data_len)
                    if self.shutdown:
                        break
                    clients = self.clients.copy()
                    for client in clients: 
                        client.send(data)
                        time.sleep(0.1) # Wait 100ms
        except Exception as ex:
            self.logger.debug("run_serial exception ex=%s", ex)

        self.logger.debug("run_serial terminated")

    def run(self):
        try:
            last_debug_dt = None
            while not self.shutdown:
                try:
                    ds = 1917 if last_debug_dt is None else (datetime.datetime.now()-last_debug_dt).total_seconds()
                    if ds>=60: 
                        self.logger.debug("waiting for a connection")
                        last_debug_dt = datetime.datetime.now()

                    connection, address = self.socket.accept()
                    self.logger.info("accepted client connection from %s", address)

                    client = TcpSerialPortClient(self, connection, address)
                    self.register_client(client)
                except socket.timeout as e:
                    pass
        except Exception as ex:
            self.shutdown = True
            self.logger.debug("run exception ex=%s", ex)

        self.logger.debug("shutting down....")
        self.socket.close()
        self.logger.debug("terminated")

    def start(self):
        server_address = ("", self.port)
        self.logger.debug("starting up on %s", server_address)

        self.socket.bind(server_address)
        self.socket.listen(1)
        self.run_thread = threading.Thread(target=self.run,args=())
        self.run_thread.start()

        self.run_serial_thread = threading.Thread(target=self.run_serial,args=())
        self.run_serial_thread.start()

    def stop(self):        
        self.logger.debug("stopping....")
        self.shutdown = True
        #self.socket.close()

        clients = self.clients.copy()
        for client in clients: 
            client.stop()

        self.logger.debug("join th:%s run_thread", self.run_thread.getName())
        self.run_thread.join()

        for client in clients: 
            self.logger.debug("join th:%s client:%s", client.run_thread.getName(), client.address)
            client.run_thread.join()

        self.logger.debug("join th:%s run_serial_thread", self.run_serial_thread.getName())
        self.run_serial_thread.join()

        self.logger.debug("stopped")

    def register_client(self, client):
        self.lock.acquire()
        try:
            self.clients.append(client)
            self.logger.debug("register client:%s #clients:%s", client.address, len(self.clients))
        finally:
            self.lock.release()

    def unregister_client(self, client):
        self.lock.acquire()
        try:
            self.clients.remove(client)
            self.logger.debug("unregister client:%s #clients:%s", client.address, len(self.clients))
        finally:
            self.lock.release()

def main():
    logging.basicConfig(format="%(process)d-%(name)s-%(levelname)s-%(message)s", level=logging.DEBUG)
    logging.info("Starting... platform=%s hostname=%s", sys.platform, socket.gethostname())

    SerialPortController.SerialPortController.list_ports()

    port_name = None
    if sys.platform == "linux" or sys.platform == "linux2":
        port_name = "/dev/ttyUSB0"
    else:
        port_name = "Com38"

    uart0_component = SerialPortController.SerialPortController(port_name, 230400)
    uart0_component.start()

    server = TcpSerialPortBridge(24, uart0_component)
    server.start()

    time.sleep(3)
    input("===> Press Enter to quit...\n")

    logging.debug("*** Enter pressed ***")

    uart0_component.stop()
    server.stop()

    logging.info("Terminated")

if __name__ == "__main__":
    main()
