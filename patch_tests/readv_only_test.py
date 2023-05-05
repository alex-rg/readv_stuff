#!/usr/bin/env python3
import argparse
import sys

from random import randint
from urllib.parse import urlparse
from os import stat

from XRootD import client
from XRootD.client.flags import QueryCode


def get_server_limits(url):
    cl = client.FileSystem(url)
    status, iov_max = cl.query(QueryCode.CONFIG, 'readv_iov_max')
    if not status.ok:
        raise RuntimeError("Get iov failed: {0}".format(status))
    status, ior_max = cl.query(QueryCode.CONFIG, 'readv_ior_max')
    if not status.ok:
        raise RuntimeError("Get ior failed: {0}".format(status))
    return int(iov_max), int(ior_max)


def random_line(filename):
    size = stat(filename).st_size
    with open(filename) as fd:
        fd.seek(randint(0, size-200))
        fd.readline()
        res = fd.readline()
    return res


def parse_args():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group()
    g.add_argument('-l', '--url_list', help="list of urls that can be used for tests")
    g.add_argument('-u', '--url', help="Url to use for tests.")
    parser.add_argument('-n', '--ntimes', help="How many readvs should be issued for a single url. Default is 1", default=1, type=int)
    parser.add_argument('-N', '--nfiles', help="How many files we should test. Default is 1", default=1, type=int)
    parser.add_argument('-t', '--test_type', help="Which test to perform: random or border.", choices=['random', 'border'], default='random')
    parser.add_argument('-s', '--silent', help="Do not print output (data read), just request status.", action='store_true')
    parser.add_argument('-S', '--scatter', help="Scatter of the readv chunks. Default if 4MB.", type=int, default=4*1024*1024)
    parser.add_argument('-c', '--chunks_sorted', help="Sort chunks in requests.", action='store_true')
    parser.add_argument('-C', '--chunks_number', help="Number of chunks in a single request.", type=int, default=1024)
    args = parser.parse_args()
    return args


def random_chunks(n, size, scatter, max_len):
    chunks = set()
    if size > scatter:
        center = randint(scatter // 2, size - scatter // 2)
        a, b =center - scatter // 2, center + scatter // 2
    else:
        a, b = 0, size - max_len
        if b < 0:
            raise ValueError("File size too small: {0} while max chunk len is {1}".format(size, max_len))
    for _ in range(n):
        chunk_len = randint(1, max_len)
        offset = randint(a, b)
        chunks.add( (offset, chunk_len) )
    return [x for x in chunks]


def border_chunks(n, size, block_size=8*1024*1024):
    chunks = set()
    if size < block_size or size < n:
        raise ValueError("File too small for border test")

    for i in range(1, size // block_size):
        chunks.add( (i*block_size-1, 2) )

    if size % block_size != 0:
        chunks.add( ((size // block_size)*block_size-1, 2) )

    while len(chunks) < n:
        chunks.add( (randint(0, size-1), 1) )
    return [x for x in chunks]


def do_readvs(file_url, scatter=128*1024*1024 + 1024*16, ntimes=2, nchunks=1024, max_len=1024, test_type='random', silent=False, sorted_chunks=True):
    with client.File() as f:
        f.open(file_url)
        status, stat = f.stat()
        print("Open status:",  status)
        if not status.ok:
            raise ValueError(f"Failed to stat file {file_url}")
        size = stat.size
        for __ in range(ntimes):
            if test_type == 'random':
                chunks = random_chunks(nchunks, size, scatter, max_len)
            elif test_type == 'border':
                chunks = border_chunks(nchunks, size)
            else:
                raise ValueError("Wrong test type: {0}".format(test_type))

            if sorted_chunks:
                chunks = sorted(chunks, key=lambda x: x[0])

            status, response = f.vector_read(chunks=chunks)
            if not status.ok:
                print(f"Failed to readv file, status={status}, resp={response}, chunks={chunks if not silent else len(chunks)}")
            else:
                print(f"Readv finished successfully: {status}", file=sys.stderr)



if __name__ == '__main__':
    args = parse_args()
    #parse_res = urlparse(url)
    #server = parse_res.scheme + '://' + parse_res.netloc
    #max_iov, max_ior = get_server_limits(server)
    #while True:
    for _ in range(args.nfiles):
        if args.url:
            url = args.url
        else:
            url = random_line(args.url_list)
        do_readvs(url, max_len=8192, test_type=args.test_type, silent=args.silent, ntimes=args.ntimes, scatter=args.scatter, sorted_chunks=args.chunks_sorted, nchunks=args.chunks_number)
