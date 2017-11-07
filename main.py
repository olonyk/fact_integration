"""
Launch point for the kernel-server.
Options:
    -i                          [Launch Interpreter ]
    -s                          [Launch Server]
    -r                          [Launch ROS subscriber]
    --data=/path/to/data/file   [Set data file]
Example:
    python main.py -isr --data=lego/Lego_DB1_shuffle1.csv
"""
import sys
from src.kernel import Kernel


def _read_command_line(commands, arg):
    if "--data=" in arg:
        data_file = arg.split("=")[0]
    elif "-" in arg:
        if "i" in arg:
            commands["interpreter"] = True
        if "s" in arg:
            commands["server"] = True
        if "r" in arg:
            commands["subscriber"] = True
    return commands

if __name__ == "__main__":
    if len(sys.argv) > 1:
        commands = {"data_file": "lego/Lego_DB1_shuffle1.csv",
                    "server":False,
                    "subscriber":False,
                    "interpreter":False}
        for arg in sys.argv:
            commands = _read_command_line(commands, arg)
        kernel = Kernel(commands)
        kernel.run()
    else:
        print(__doc__)