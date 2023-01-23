#!/usr/bin/env python3

import sys
from pyxrootd import client

if __name__ == '__main__':
    url = sys.argv[1]
    with client.File() as fd:
        res = fd.open(url)
        print(res)
        try:
            chunks = eval(sys.argv[2])
        except IndexError:
            chunks = [(1000000000, 10), (50000000, 10)]
        status, res = fd.vector_read(chunks)

    print(status, res)
    print(status)
