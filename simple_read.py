#!/usr/bin/env python3

import sys
import time
from pyxrootd import client

if __name__ == '__main__':
    url = sys.argv[1]
    with client.File() as fd:
        res = fd.open(url)
        print("Open res:", res)
        try:
            coords = eval(sys.argv[2])
        except IndexError:
            coords = [1000, 10]
        #status, res = fd.vector_read(chunks)
        status, res = fd.read(coords[0], coords[1])
        print(status)
        print(res)
