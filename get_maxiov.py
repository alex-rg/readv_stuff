#!/usr/bin/env python
import sys

from XRootD import client as xrd_client
from XRootD.client.flags import QueryCode


def get_max_iov(url):
    fs = xrd_client.FileSystem(url)
    status, response = fs.query(QueryCode.CONFIG, 'readv_iov_max')
    if not status.ok:
        raise RuntimeError("Can not query server: {0}".format(status))
    return int(response.strip())

if __name__ == '__main__':
    print(get_max_iov(sys.argv[1]))
