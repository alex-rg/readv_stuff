#!/usr/bin/env python2
from __future__ import print_function

import os
import sys
import pytest

from random import randint

from XRootD import client
from XRootD.client.flags import QueryCode

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse




class TestReadv:
    def read(self, chunks):
        res = []
        with client.File() as f:
            st, _ = f.open(self.url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for read: {1}".format(self.url, st))

            for off, sz in chunks:
                st, tres = f.read(offset=off, size=sz)
                if not st.ok:
                    raise RuntimeError("Can not read file {0} at {1},{2}: {3}".format(self.url, off, sz, st))
                res.append(tres) 

        return res

    def readv(self, chunks):
        res = []
        with client.File() as f:
            st, _ = f.open(self.url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for read: {1}".format(self.url, st))

            st, tres = f.vector_read(chunks)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for read: {1}".format(self.url, st))

        for chk in tres.chunks:
            res.append(chk.buffer)

        return res

    @staticmethod
    def get_max_iov(url):
        cl = client.FileSystem(url)
        status, response = cl.query(QueryCode.CONFIG, 'readv_iov_max')

        if not status.ok:
            raise RuntimeError("Can not query server: {0}".format(status))

        return int(response.strip())

    @staticmethod
    def file_size(url):
        with client.File() as f:
            st, _ = f.open(url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for stat: {1}".format(url, st))
            st, res = f.stat()
            if not st.ok:
                raise RuntimeError("Can not stat file {0}: {1}".format(url, st))
            return res.size

    @classmethod
    def setup_class(cls):
        for attr, varname in [('url', 'TEST_FILE_URL'), ('block_size', 'FILE_BLOCK_SIZE')]:
            try:
                setattr(cls, attr, os.environ[varname])
            except KeyError:
                raise RuntimeError("Environment variable {0} not set -- set it, please.".format(varname))
        cls.block_size = int(cls.block_size)
        purl = urlparse(cls.url)
        cls.max_iov = cls.get_max_iov(purl.scheme + '://' + purl.netloc)
        cls.file_size = cls.file_size(cls.url)

    @pytest.fixture
    def max_stable_chunks(self):
        rmnd = self.file_size % self.max_iov
        if rmnd != 0:
            step = self.file_size // self.max_iov
            chunk = rmnd
        else:
            step = self.file_size // self.max_iov - 1
            chunk = self.max_iov
        return [(i*step, chunk) for i in range(1, self.max_iov+1)]

    @pytest.fixture
    def random_chunks(self):
        chunks = []
        min_size = 10
        max_size = 128
        for _ in range(randint(1, self.max_iov)):
            chunks.append( (randint(0, self.file_size - max_size), randint(min_size, max_size)) )
        return chunks

    @pytest.fixture
    def block_borders(self):
        nchunks = self.file_size // self.block_size
        print([(i, self.block_size+1) for i in range(0, self.file_size-self.block_size, 2*self.block_size) ] )
        return [(i*(self.block_size)-1, 2) for i in range(1, min(self.max_iov, nchunks)) ]

    @pytest.fixture
    def wholefile(self):
        nchunks = self.file_size // block_size
        chunks = [(i*self.file_size, self.block_size)]

    def do_compare(self, chunks):
        r1 = self.read(chunks)
        r2 = self.readv(chunks)
        for d1, d2 in zip(r1, r2):
            assert d1 == d2

    def test_max_chunks(self, max_stable_chunks):
        "Test readv with maximum number of chunks"
        assert max_stable_chunks[-1][0] + max_stable_chunks[-1][1] == self.file_size
        assert len(max_stable_chunks) == self.max_iov
        self.do_compare(max_stable_chunks)

    def test_random_chunks(self, random_chunks):
        "Test readv with random chunks"
        self.do_compare(random_chunks)

    def test_block_plus_one_chunks(self, block_borders):
        "Test readv with chunks spanning multiple blocks"
        self.do_compare(block_borders)


if __name__ == '__main__':
    url = sys.argv[1]
    to_read = [(0,10), (129, 20), (4*1024*1024 -10, 10), (8*1024*1024-10, 11)]
    TestReadv.setup_class()
    cls = TestReadv
    test_suite = TestReadv()
    chunks = test_suite.max_stable_chunks()
    for chk in test_suite.readv(chunks):
        print(chk) 
