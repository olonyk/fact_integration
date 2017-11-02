from .server import Server
from .interpreter import Interpreter
import time
import subprocess
from os.path import realpath, dirname, join

class Kernel(object):
    def __init__(self):
        """ Initialize the TCP/IP server, ROS subscriber and the parser. 
        """
        self.server = Server()
        self.interpreter = Interpreter()
    
    def run(self):
        print("Kernel running")
        self.server.start()
        time.sleep(3)
        self.interpreter.start()
        subscriber = subprocess.call((['python2.7', join(dirname(realpath(__file__)),
                                                                 "subscriber.py")]))
        print("Kernel terminating")
    