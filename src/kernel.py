from .server import Server
from .subscriber import Subscriber
import time

class Kernel(object):
    def __init__(self):
        """ Initialize the TCP/IP server, ROS subscriber and the parser. 
        """
        self.server = Server()
        self.subscriber = Subscriber()
    
    def run(self):
        print("Kernel running")
        self.server.start()
        time.sleep(1)
        self.subscriber.start()
        print("Kernel terminating")
    