from .server import Server
from .subscriber import Subscriber

class Kernel(object):
    def __init__(self):
        """ Initialize the TCP/IP server, ROS subscriber and the parser. 
        """
        self.server = Server()
        self.Subscriber = Subscriber()
    
    def run(self):
        print("Kernel running")

    