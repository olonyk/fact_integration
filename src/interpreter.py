import csv
import os
import re
import select
import sys
from math import pow, sqrt
from multiprocessing import Process
from os.path import dirname, join

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
        self.active_filters = None
        self.filtered_items = None
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
        """
        data = data.split(";")
        header = data.pop(0)
        if header == "update":
            self.update(data)
        elif header == "action":
            self.action(data)
        elif header == "confirm":
            self.confirm(data)

    def action(self, action_msg):
        """ Update the data-base
        param: action_msg [String, format defined in README.md]
        return: N/A
        """
        action_dict = {}
        for command in action_msg:
            action_dict[command.split(":")[0]] = command.split(":")[1]
            
        filtered_items = list(self.mongo_db.find({"#Color": gui.color.get(),
                                                  "#Shape": gui.shape.get()},
                                                  {"<img>": 1, "_id": 0, "ID":1, "X":1, "Y":1}))

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
        os.write(self.pipe_out, msg.encode("utf-8"))
        sys.stdout.flush()

    def reset(self):
        """ Reset the variables for a new round.
        param: N/A
        return: N/A
        """
        self.current_action = None
        self.active_filters = None
        self.filtered_items = None

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
