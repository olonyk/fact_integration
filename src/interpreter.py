import csv
import os
import re
import select
import sys
from math import pow, sqrt
from multiprocessing import Process
from os.path import dirname, join
from datetime import datetime

from bson.binary import Binary
from pymongo import MongoClient

from .client import Client


class Interpreter(Process):
    """ The Interpreter-class is a intermediator between the arcitecture and the ROS-network.
    """
    def __init__(self, data_base_file):
        """ Constructor
        param: data_base_file [path]
        return: Interpreter [Process]
        """
        super(Interpreter, self).__init__()

        # Create a pipe to communicate to the client process
        self.pipe_in_client, self.pipe_out = os.pipe()
        self.pipe_in, self.pipe_out_client = os.pipe()
        # Create a client object to communicate with the server
        self.client = Client(client_type="interpreter",
                             pipe_in=self.pipe_in_client,
                             pipe_out=self.pipe_out_client)
        self.client.start()

        # Create and initialize the variables
        self.current_action = None
        self.action_dict = {}
        self.filtered_items = []
        self.current_block = None
        self.reset()

        # Read data base and format it into a mongo_db object
        self.mongo_db = self.build(data_base_file)

    def run(self):
        """ Main loop.
        param: N/A
        return: N/A
        """
        while True:
            # Wait for incomming message from the server (via the client)
            socket_list = [self.pipe_in]

            # Get the list sockets which are readable
            read_sockets, _, _ = select.select(socket_list, [], [])

            for sock in read_sockets:
                # Incoming message from remote server
                if sock == self.pipe_in:
                    data = os.read(self.pipe_in, 4096)
                    if not data:
                        print('\nDisconnected from server')
                        sys.exit()
                    else:
                        self.parse(data.decode("utf-8"))

    def parse(self, data):
        """ Interperet the incomming message and take appropriate action.
        param: data [String, format defined in README.md]
        return: N/A

        {'skills': ['pick'], 'attributes': ['red'], 'objects': ['block'], 'feedback': []}
        {'skills': [], 'attributes': [], 'objects': [], 'feedback': ['yes']}
        {'skills': [], 'attributes': [], 'objects': [], 'feedback': ['no']}
        {'skills': ['pick'], 'attributes': [], 'objects': ['Square', 'Red', 'block'], 'feedback': []}
        {'skills': [], 'attributes': ['red'], 'objects': [], 'feedback': []}
        {'skills': [], 'attributes': ['blue'], 'objects': ['lego'], 'feedback': []}
        """
        data = self.format_input(data)
        #data = data.split(";")
        header = data.pop(0)
        if header == "update":
            self.update(data)
        elif header == "action":
            self.action(data)
        elif header == "confirm":
            self.confirm(data)
        self.print_state()

    def format_input(self, data):
        """ Interperet the incomming message and take appropriate action.
        param: data [String, format defined in README.md]
        return: formatted_data [dictionary]
        """"
        data.replace("{", "")
        data.replace("}", "")
        data.replace("[", "")
        data.replace("]", "")
        data.replace("'", "")
        data.replace("$", "")
        # Format json ??
        formatted_data = {}

        return formatted_data

    def confirm(self, confirm_msg):
        """ Interperet the confirm message, either positive or negative, i.e. either tell YuMi to
        execute the action or test a new block.
        param: confirm_msg [String, format defined in README.md]
        return: N/A
        """
        # If a confirmation is recieved, send execute command to yumi, remove the block from the 
        # data base and send a speech command to hololens.
        if "true" in confirm_msg:
            self.send("yumi;execute$")
            self.remove(self.current_block)
            self.send("hololens;speech;ok$")
        # If a negation is recieved and there are blocks still in the list then try the next block
        # in the list, else start over
        else:
            if self.filtered_items:
                self.current_block = self.filtered_items.pop(0)
                self.send("yumi;{};{},{}$".format(self.current_action,
                                                  self.current_block["X"],
                                                  self.current_block["Y"]))
            else:
                self.reset()

    def remove(self, block):
        """ Remove the specified block from the pymongo database
        param: block [Dict]
        return: N/A
        """
        self.mongo_db.delete_one({"ID": block[0]})

    def action(self, action_msg):
        """ Update the data-base
        param: action_msg [String, format defined in README.md]
        return: N/A
        """
        for command in action_msg:
            self.action_dict[command.split(":")[0]] = command.split(":")[1]

        # Update or set the current action
        if "action" in self.action_dict.keys():
            self.current_action = self.action_dict["action"]
            self.action_dict.pop("action")
        self.filtered_items = list(self.mongo_db.find(self.action_dict,
                                                      {"_id": 0, "ID":1, "X":1, "Y":1}))
        # Decide what to do
        # No objects are found, the current turn is restarted.
        if not self.filtered_items:
            self.reset()
        # If only a few objects remain in the data base, the action is visualized to the user.
        elif len(self.filtered_items) < 4:
            self.current_block = self.filtered_items.pop(0)
            self.send("yumi;{};{},{}$".format(self.current_action,
                                              self.current_block["X"],
                                              self.current_block["Y"]))
        # If there are many objects left the hololens will highlight the ones considered
        else:
            msg = []
            for item in self.filtered_items:
                msg.append("{},{},{}".format(item["ID"], item["X"][:5], item["Y"][:5]))
            msg = ";".join(msg)
            msg = "{};{}$".format("hololens", msg)
            self.send(msg)

    def update(self, update_msg):
        """ Update the data-base
        param: update_msg [String, format defined in README.md]
        return: N/A
        """
        for block in update_msg:
            block = block.split(",")
            if len(block) > 1:
                self.update_block(block)

    def update_block(self, block):
        """ Find the closest block and update it
        param: data [String, format defined in README.md]
        return: N/A
        """
        all_items = list(self.mongo_db.find({}, {"_id": 1, "ID":1, "X":1, "Y":1}))
        min_dist = 1000
        item_2_update = None

        post = {"X":block[0], "Y":block[1]}
        if len(block) > 2:
            post[block[2].split(":")[0]] = block[2].split(":")[1]
        if len(block) > 2:
            post[block[3].split(":")[0]] = block[3].split(":")[1]

        for i, item in enumerate(all_items):
            dist = self.euclidian(post["X"], post["Y"], item["X"], item["Y"])
            if dist < min_dist:
                min_dist = dist
                item_2_update = item
        if item_2_update and min_dist <= 0.02:
            self.mongo_db.update_one({'_id':item_2_update['_id']}, {"$set": post}, upsert=False)
        else:
            print("Min closest block was {:.02f}cm away, no update".format(min_dist*100))

    def euclidian(self, x1, y1, x2, y2):
        return sqrt(pow(float(x1)-float(x2), 2)+pow(float(y1)-float(y2), 2))


    def send(self, msg):
        """ Sends a message
        param: msg [String]
        return: N/A
        """
        self.log("Interpreter is sending: {}".format(msg))
        os.write(self.pipe_out, msg.encode("utf-8"))
        sys.stdout.flush()

    def reset(self):
        """ Reset the variables for a new round.
        param: N/A
        return: N/A
        """
        self.current_action = None
        self.action_dict = {}
        self.filtered_items = []
        self.current_block = None

    def build(self, data_base_file):
        """ Read data base and format it into a mongo_db object
        param: data_base_file [path]
        return: db.objects [mongo_db object]
        """ 
        data_dir = dirname(data_base_file)
        # Read the given CSV file
        with open(data_base_file, newline='') as csvfile:
            raw_data = list(csv.reader(csvfile, delimiter=";"))

        # Pop the header to use as a reference for the fields in the data base
        header = raw_data.pop(0)

        # Create the database to fill with data
        client = MongoClient()
        db = client.database

        # Iterate through the raw data and insert it to the MongoDB
        posts = []
        img_idx = header.index("<img>")
        nam_idx = header.index("#Name")
        col_idx = header.index("#Color")
        header.append("#Shape")
        for data_row in raw_data:
            # Format the image
            image_file = open(join(data_dir, data_row[img_idx]), 'rb').read()
            data_row[img_idx] = Binary(image_file)

            # Color to lower case
            data_row[col_idx] = data_row[col_idx].lower()

            # Add a shape tag
            data_row.append(self.get_shape(data_row[nam_idx]))

            # Add the entry to post
            posts.append({tag : data for tag, data in zip(header, data_row)})

        # Remove all posts in db
        db.objects.remove({})

        # Insert new documents
        db.objects.insert_many(posts)
        return db.objects

    def get_shape(self, name):
        regex = r"^Brick \d+[X]\d+"
        if "Roof Tile" in name:
            return "slope"
        elif re.match( regex, name, re.M|re.I):
            return "regular"
        return "round"

    def log(self, message):
        """ Add a time stamp and write the message to the log file.
        """
        time = datetime.now()
        time_stamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}\t".format(time.year, time.month,\
                                                                          time.day, time.hour, \
                                                                          time.minute, time.second)
        print("{}\t{}".format(time_stamp, message))
    
    def print_state(self):
        print("======Interpeter state======")
        print("current action:\t{}".format(self.current_action))
        print("nr items      :\t{}".format(len(self.filtered_items)))
        if self.current_block:
            print("current_block:\t{} at ({}, {})".format(self.current_block["ID"], self.current_block["X"], self.current_block["Y"]))
        else:
            print("current_block:\tNone")
        
        print("filer:")
        for key, value in self.action_dict.items():
            print("\t{}:\t{}".format(key, value))
