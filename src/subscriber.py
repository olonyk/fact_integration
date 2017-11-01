import os
import sys
from multiprocessing import Process

import rospy
import std_msgs.msg
import trajectory_msgs.msg

from .client import Client


class Subscriber(Process):
    def __init__(self):
        """ Constructor
        """
        super(Subscriber ,self).__init__()

        # Create a pipe to communicate to the client process
        self.pipe_in_client, self.pipe_out = os.pipe()
        self.pipe_in, self.pipe_out_client = os.pipe()
        # Create a client object to communicate with the server
        self.client = Client(client_type="subscriber",
                             pipe_in=self.pipe_in_client,
                             pipe_out=self.pipe_out_client)
        self.client.start() 
    
    def parse(self, data):
        """ Parsing trajectory data and sending it to hololens.
        """
        print "Listener heard something"
        positions = [[str(position) for position in point.positions] for point in data.points]
        positions.insert(0, data.joint_names)
        positions = ";".join([",".join(position) for position in positions])
        positions = "hololens;trajectory;" + positions
        os.write(self.pipe_out, positions.encode("utf-8"))
        sys.stdout.flush()

    def listen(self):
        """ main loop
        """
        print "Listening..."
        rospy.init_node('listener', anonymous=True)
        rospy.Subscriber("/yumi/traj_moveit", trajectory_msgs.msg.JointTrajectory, self.parse)
        # spin() simply keeps python from exiting until this node is stopped
        rospy.spin()
    
    def run(self):
        """ Main loop
        """
        
        print("New loop")
        self.listen()
