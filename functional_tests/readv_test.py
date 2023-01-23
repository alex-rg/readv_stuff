#!/usr/bin/env python2
from __future__ import print_function

import re
import os
import sys
import zlib
import pytest
import subprocess

from itertools import product
from random import randint
from tempfile import mkstemp
from abc import ABC, abstractmethod

from XRootD import client as xrd_client
from XRootD.client.flags import QueryCode

from file_access_clients import FallbackClient, PyXrootdClient, GfalCMDClient


TEST_FILE_SIZE = 100*1024*1024
CACHE_SIZE = 4*1024*1024


class TestReadv:
    @staticmethod
    def adler32(data):
        cksum = hex(zlib.adler32(data))[2:]
        if len(cksum) < 8:
            cksum = '0' * (8 - len(cksum)) + cksum
        return cksum

    @pytest.fixture(scope='class')
    def test_file_content(self):
        return os.urandom(TEST_FILE_SIZE)

    @pytest.fixture(scope='class')
    def test_file_checksum(self, test_file_content):
        return self.adler32(test_file_content)

    @pytest.fixture(scope='class')
    def test_file_creation_result(self, test_file_content, request):
        fd, testfile = mkstemp(dir='./tmp')
        bytes_written = os.write(fd, test_file_content)
        os.close(fd)
        assert bytes_written == TEST_FILE_SIZE
        yield bytes_written, testfile
        if request.node.session.testsfailed == 0:
            os.unlink(testfile)

    @pytest.fixture(scope='class')
    def test_file(self, test_file_creation_result):
        return test_file_creation_result[1]

    @pytest.fixture(scope='class')
    def test_file_size(self, test_file_creation_result):
        return test_file_creation_result[0]

    @pytest.fixture
    def download_path(self, test_file, scope='class'):
        path = test_file + '_download'
        yield path
        if os.path.exists(path):
           os.unlink(path)

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

    @pytest.fixture(
            params=product(
                    [2**i for i in range(1, 11)],
                    [i for i in range(1, 11)],
                    [2**i for i in range(8, 16)] + [randint(1,1025)],
                    [i for i in range(CACHE_SIZE, TEST_FILE_SIZE, 3*CACHE_SIZE)],
                )
        )
    def random_chunks(self, test_file_size, request):
        chunks = set()
        n, min_size, max_size, request_end = request.param
        for _ in range(n):
            if request_end > max_size:
                b = request_end - max_size
            else:
                b = 0
                max_size = request_end
            chunks.add( (randint(0, b), randint(min_size, max_size)) )
        chunks = [x for x in chunks]
        chunks = sorted(chunks, key=lambda x: x[0])
        return chunks

    @pytest.fixture(params=[i for i in range(1, 1025)])
    def random_chunks_one_byte(self, test_file_size, request):
        "Random chunks with 1 byte length"
        chunks = set()
        n = request.param
        for _ in range(n):
            chunks.add( (randint(0, test_file_size - 1), 1) )
        chunks = [x for x in chunks]
        chunks = sorted(chunks, key=lambda x: x[0])
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

    def do_compare(self, chunks, localfile, chunks2=None, chunks3=None):
        assert len(chunks) > 0

        if chunks2 is None:
            chunks2 = chunks
        if chunks3 is None:
            chunks3 = chunks

        r1 = self.client.read(chunks)
        r2 = self.client.readv(chunks2)
        r3 = self.read_local(chunks3, localfile)
        print("CHUNKS=", chunks)
        for d1, d2, d3 in zip(r1, r2, r3):
            assert d1 == d2 == d3

    def test_copy(self, test_file):
        "Test copy"
        copy_res, copy_message = self.client.upload_file(test_file)
        print(copy_message)
        assert copy_res == 0

    def test_download(self, test_file, download_path, file_checksum):
        "Test file download"
        copy_res, copy_message = self.client.download_file(download_path)
        print(copy_message)
        assert copy_res == 0
        with open(download_path, 'rb') as fd:
            content = fd.read()
        local_cksum = self.adler32(content)
        assert local_cksum == file_checksum[1]

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

    def test_random_chunks_one_byte(self, random_chunks_one_byte, test_file):
        "Test readv with random chunks of 1 byte length"
        self.do_compare(random_chunks_one_byte, test_file)

    def test_block_plus_one_chunks(self, block_borders, test_file):
        "Test readv with chunks spanning multiple blocks"
        self.do_compare(block_borders, test_file)

    @pytest.mark.xfail(strict=True)
    def test_consistency(self, block_borders, test_file, test_file_size):
        "Make sure that compare function does compare something"
        if test_file_size >= 3*1024:
            chunks = [(0, 1024)]
            chunks2 = [(1025, 2048)]
            chunks3 = [(2049,3072)]
            self.do_compare(chunks, test_file, chunks2=chunks2, chunks3=chunks3)

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
