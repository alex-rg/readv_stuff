#!/usr/bin/env python2
from __future__ import print_function

import re
import os
import sys
import zlib
import pytest
import subprocess

from random import randint
from tempfile import mkstemp
from abc import ABC, abstractmethod

from XRootD import client as xrd_client
from XRootD.client.flags import QueryCode

from file_access_clients import FallbackClient, PyXrootdClient, GfalCMDClient


TEST_FILE_SIZE = 100*1024*1024




class TestReadv:

    @pytest.fixture(scope='class')
    def test_file_content(self):
        return os.urandom(TEST_FILE_SIZE)

    @pytest.fixture(scope='class')
    def test_file_checksum(self, test_file_content):
        cksum = hex(zlib.adler32(test_file_content))[2:]
        if len(cksum) < 8:
            cksum = '0' * (8 - len(cksum)) + cksum
        return cksum

    @pytest.fixture(scope='class')
    def test_file_creation_result(self, test_file_content):
        fd, testfile = mkstemp(dir='./tmp')
        bytes_written = os.write(fd, test_file_content)
        os.close(fd)
        assert bytes_written == TEST_FILE_SIZE
        yield bytes_written, testfile
        os.unlink(testfile)

    @pytest.fixture(scope='class')
    def test_file(self, test_file_creation_result):
        return test_file_creation_result[1]

    @pytest.fixture(scope='class')
    def test_file_size(self, test_file_creation_result):
        return test_file_creation_result[0]

    @classmethod
    def setup_class(cls):
        for attr, varname in [('url', 'TEST_FILE_URL'), ('block_size', 'FILE_BLOCK_SIZE')]:
            try:
                setattr(cls, attr, os.environ[varname])
            except KeyError:
                raise RuntimeError("Environment variable {0} not set -- set it, please.".format(varname))
        cls.block_size = int(cls.block_size)

        #Get client
        root_client = PyXrootdClient(cls.url)
        https_client = GfalCMDClient(root_client.https_url)
        cls.client = FallbackClient(clients=[root_client, https_client], fallback_methods=['upload_file', 'delete_file'])
        cls.max_iov = cls.client.get_max_iov()

    @pytest.fixture
    def file_stat(self):
        return self.client.stat_file()

    @pytest.fixture
    def file_checksum(self):
        return self.client.get_file_checksum()

    @pytest.fixture
    def single_chunk(self):
        return [(0, 10)]

    @pytest.fixture
    def max_stable_chunks(self, test_file_size):
        rmnd = test_file_size % self.max_iov
        if rmnd != 0:
            step = test_.file_size // self.max_iov
            chunk = rmnd
        else:
            step = test_file_size // self.max_iov - 1
            chunk = self.max_iov
        return [(i*step, chunk) for i in range(1, self.max_iov+1)]

    @pytest.fixture
    def random_chunks(self, test_file_size):
        chunks = []
        min_size = 10
        max_size = 128
        for _ in range(randint(1, self.max_iov)):
            chunks.append( (randint(0, test_file_size - max_size), randint(min_size, max_size)) )
        return chunks

    @pytest.fixture
    def block_borders(self, test_file_size):
        nchunks = test_file_size // self.block_size
        return [(i*(self.block_size)-1, 2) for i in range(1, min(self.max_iov, nchunks)+1) ]

    @pytest.fixture
    def wholefile(self, test_file_size):
        nchunks = test_file_size // block_size
        chunks = [(i*self.file_size, self.block_size)]

    def read_local(self, chunks, localfile):
        res = []
        with open(localfile, 'rb') as fd:
            for off, sz in chunks:
                fd.seek(off)
                res.append(fd.read(sz))
        return res

    def do_compare(self, chunks, localfile):
        assert len(chunks) > 0
        r1 = self.client.read(chunks)
        r2 = self.client.readv(chunks)
        r3 = self.read_local(chunks, localfile)
        for d1, d2, d3 in zip(r1, r2, r3):
            assert d1 == d2 == d3

    def test_copy(self, test_file):
        "Test copy"
        copy_res, copy_message = self.client.upload_file(test_file)
        print(copy_message)
        assert copy_res == 0

    def test_filesize(self, file_stat, test_file_size):
        "test that file size on server match the real one"
        assert file_stat.size == test_file_size

    def test_checksum(self, file_checksum, test_file_checksum):
        "test that file size on server match the real one"
        assert file_checksum[1] == test_file_checksum

    def test_single_chunk(self, single_chunk, test_file):
        "Test readv with one chunk"
        self.do_compare(single_chunk, test_file)

    def test_max_chunks(self, max_stable_chunks, test_file, test_file_size):
        "Test readv with maximum number of chunks"
        assert max_stable_chunks[-1][0] + max_stable_chunks[-1][1] == test_file_size
        assert len(max_stable_chunks) == self.max_iov
        self.do_compare(max_stable_chunks, test_file)

    def test_random_chunks(self, random_chunks, test_file):
        "Test readv with random chunks"
        self.do_compare(random_chunks, test_file)

    def test_block_plus_one_chunks(self, block_borders, test_file):
        "Test readv with chunks spanning multiple blocks"
        self.do_compare(block_borders, test_file)

    def test_delete(self):
        "Test file deletion"
        res, message = self.client.delete_file()
        print(message)
        assert res == 0


if __name__ == '__main__':
    url = sys.argv[1]
    cl_root = PyXrootdClient(url)
    cl_gfal = GfalCMDClient(cl_root.https_url)
    client = FallbackClient(clients=[cl_root, cl_gfal])
    TestReadv.setup_class()
    tcl = TestReadv()
    #print(client.upload_file('/etc/centos-release'))
    print(tcl.do_compare([(82615664, 87), (68552208, 64), (73253419, 62), (1012527, 77), (101888140, 98), (43431262, 64)]))
