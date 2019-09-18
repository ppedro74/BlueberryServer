import os
import sys
import logging
import socket
import threading
import time
import datetime
import logging
import psutil
#import netifaces
import Controller

class UdpBroadcaster(Controller.Controller):
    DEBUG_INTERVAL = 5 * 60 # 5 minutes

    def __init__(self, name, port, delay, log_level):
        self.name = name
        self.port = port
        self.delay = delay
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.shutdown = False
        self.last_debug_dt = None

    def start(self):
        self.logger.debug("Starting port=%s", self.port)
        try:
            self.run_thread = threading.Thread(target=self.run,args=())
            self.run_thread.start()
        except socket.error as ex:
            self.shutdown = True
            self.logger.error("start ex=%s", ex)

    def stop(self):        
        self.logger.debug("stopping....")
        self.shutdown = True
        self.logger.debug("join th:%s run_thread", self.run_thread.getName())
        self.run_thread.join()
        self.logger.debug("stopped")

    def run(self):
        self.logger.debug("running....")
        try:
            while not self.shutdown:
                self.broadcast()
                time.sleep(self.delay)
        except Exception as ex:
            self.shutdown = True
            self.logger.error("run ex=%s", ex)

        self.logger.debug("terminated")

    def broadcast(self):
        addresses = self.get_valid_ip4_addresses()
        ds = 1917 if self.last_debug_dt is None else (datetime.datetime.now()-self.last_debug_dt).total_seconds()
        if ds>=self.DEBUG_INTERVAL:
            self.logger.debug("broadcaster ip4 addresses found:%s", addresses)
            self.last_debug_dt = datetime.datetime.now()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        hostname = socket.gethostname()
        for addr in addresses:
            #message = "{}||{}-Server||{}||{}".format(type, hostname, addr, port)
            message = self.get_message(hostname, addr)
            sock.sendto(bytes(message, "utf8"), ("<broadcast>",self.port))
            time.sleep(0.1)
        sock.close()

    def get_message(self, hostname, addr):
        return "Hello world"

    #def get_ip_addresses_using_netifaces(family=netifaces.AF_INET):
    #    ip_list = []
    #    for interface in netifaces.interfaces():
    #        links = netifaces.ifaddresses(interface)
    #
    #        for link in ifaddresses(interface)[family]:
    #            ip_list.append(link["addr"])
    #    return ip_list

    def get_ip_addresses(self, family=socket.AF_INET):
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == family:
                    yield (interface, snic.address)


    def get_valid_ip4_addresses(self):
        return [s[1] for s in self.get_ip_addresses() if not s[1].startswith(("127.", "169.254."))]

def test():
    logging.basicConfig(format="%(process)d-%(levelname)s-%(message)s", level=logging.DEBUG)
    logging.info("Starting... platform=%s", sys.platform)

    broadcaster = UdpBroadcaster("TestUdpBroadcaster", 4242, 3)
    broadcaster.start()
    input("Press Enter to continue...")
    broadcaster.stop()
    
if __name__ == "__main__":
    test()