from .server import Server
from .interpreter import Interpreter
import time
import subprocess
from os.path import realpath, dirname, join

class Kernel(object):
    def __init__(self, commands):
        """ Initialize the TCP/IP server, ROS subscriber and the parser. 
        """
        if commands["server"]:
            self.server = Server()
        if commands["interpreter"]:
            self.interpreter = Interpreter(commands["data_file"])
        self.commands = commands
    
    def run(self):
        if self.commands["server"]:
            self.server.start()
            # Wait a second so that the server is up before the other processes starts.
            time.sleep(1)
        if self.commands["interpreter"]:
            self.interpreter.start()
        if self.commands["subscriber"]:
            subprocess.call((['python2.7', join(dirname(realpath(__file__)), "subscriber.py")]))
    