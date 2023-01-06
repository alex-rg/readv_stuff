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
    def read_local(self, chunks):
        res = []
        with open(self.testfile, 'rb') as fd:
            for off, sz in chunks:
                fd.seek(off)
                res.append(fd.read(sz))
        return res

    @classmethod
    def setup_class(cls):
        for attr, varname in [('url', 'TEST_FILE_URL'), ('block_size', 'FILE_BLOCK_SIZE')]:
            try:
                setattr(cls, attr, os.environ[varname])
            except KeyError:
                raise RuntimeError("Environment variable {0} not set -- set it, please.".format(varname))
        cls.block_size = int(cls.block_size)


        #Genterate file's content, compute its checksum
        file_content = os.urandom(TEST_FILE_SIZE)
        cls.original_cksum = hex(zlib.adler32(file_content))[2:]
        if len(cls.original_cksum) < 8:
            cls.original_cksum = '0' * (8 - len(cls.original_cksum)) + cls.original_cksum

        #Create test file
        fd, cls.testfile = mkstemp(dir='./tmp')
        bytes_written = os.write(fd, file_content)
        os.close(fd)

        if bytes_written != TEST_FILE_SIZE:
            raise RuntimeError("Can not write {0} bytes to local file, {1} written.".format(TEST_FILE_SIZE, bytes_written))
        cls.file_size = bytes_written

        #Get client
        root_client = PyXrootdClient(cls.url)
        https_client = GfalCMDClient(root_client.https_url)
        cls.client = FallbackClient(clients=[root_client, https_client], fallback_methods=['upload_file', 'delete_file'])
        cls.max_iov = cls.client.get_max_iov()

        #Upload file
        cls.copy_res, cls.copy_message = cls.client.upload_file(cls.testfile)

    @classmethod
    def teardown_class(cls):
        cls.client.delete_file()
        os.unlink(cls.testfile)
        #cls.testfile_fd.close()

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
        return [(i*(self.block_size)-1, 2) for i in range(1, min(self.max_iov, nchunks)+1) ]

    @pytest.fixture
    def wholefile(self):
        nchunks = self.file_size // block_size
        chunks = [(i*self.file_size, self.block_size)]

    def do_compare(self, chunks):
        assert len(chunks) > 0
        r1 = self.client.read(chunks)
        r2 = self.client.readv(chunks)
        r3 = self.read_local(chunks)
        for d1, d2, d3 in zip(r1, r2, r3):
            assert d1 == d2 == d3

    def test_copy(self):
        "Test async copy"
        print(self.copy_message)
        assert self.copy_res == 0

    def test_filesize(self, file_stat):
        "test that file size on server match the real one"
        assert file_stat.size == self.file_size

    def test_checksum(self, file_checksum):
        "test that file size on server match the real one"
        assert file_checksum[1] == self.original_cksum

    def test_single_chunk(self, single_chunk):
        "Test readv with one chunk"
        self.do_compare(single_chunk)

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
    cl_root = PyXrootdClient(url)
    cl_gfal = GfalCMDClient(cl_root.https_url)
    client = FallbackClient(clients=[cl_root, cl_gfal])
    TestReadv.setup_class()
    tcl = TestReadv()
    #print(client.upload_file('/etc/centos-release'))
    print(tcl.do_compare([(82615664, 87), (68552208, 64), (73253419, 62), (1012527, 77), (101888140, 98), (43431262, 64)]))
