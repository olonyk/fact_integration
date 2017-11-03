"""
Launch point for the kernel-server.
"""
import sys
from src.kernel import Kernel

if __name__ == "__main__":
    data_base_file = sys.argv[1]
    kernel = Kernel(data_base_file)
    kernel.run() 