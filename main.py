"""
Launch point for the kernel-server.
"""

from src.kernel import Kernel

if __name__ == "__main__":
    kernel = Kernel()
    kernel.run() 