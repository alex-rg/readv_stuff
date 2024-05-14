#!/usr/bin/env python3
import argparse
import math
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
    g.add_argument('-d', '--dump_url', help="Url of the storage dump.")
    parser.add_argument('-n', '--ntimes', help="How many readvs should be issued for a single url. Default is 1", default=1, type=int)
    parser.add_argument('-N', '--nfiles', help="How many files we should test. Default is 1", default=1, type=int)
    parser.add_argument('-t', '--test_type', help="Which test to perform: random or border.", choices=['random', 'border', 'lhcb_job'], default='random')
    parser.add_argument('-s', '--silent', help="Do not print output (data read), just request status.", action='store_true')
    parser.add_argument('-S', '--scatter', help="Scatter of the readv chunks. Default if 4MB.", type=int, default=4*1024*1024)
    parser.add_argument('-c', '--chunks_sorted', help="Sort chunks in requests.", action='store_true')
    parser.add_argument('-C', '--chunks_number', help="Number of chunks in a single request.", type=int, default=1024)
    args = parser.parse_args()
    return args


def random_chunks(n, size, scatter, max_len, interval=None):
    chunks = set()
    if interval is None:
        if size > scatter:
            center = randint(scatter // 2, size - scatter // 2)
            a, b =center - scatter // 2, center + scatter // 2
        else:
            a, b = 0, size - max_len
            if b < 0:
                raise ValueError("File size too small: {0} while max chunk len is {1}".format(size, max_len))
    else:
        a, b = interval
    for _ in range(n):
        chunk_len = randint(1, max_len)
        offset = randint(a, b)
        chunks.add( (offset, chunk_len) )
    return [x for x in chunks]


def jobsim_chunks(n, size, scatter, max_len, max_iter, itr):
    #if hasattr(jobsim_chunks, "iter"):
    #    jobsim_chunks.iter += 1
    #else:
    #    jobsim_chunks.iter = 1
    if itr > max_iter:
        itr = 1
    if scatter + max_len + 1 > size:
        raise ValueError("File size is too small: {0} while scatter is {1}".format(size, scatter))

    if itr == 1:
        interval = (0, scatter)
    elif itr == 2:
        interval = (size - scatter - max_len - 1, size - 1 - max_len)
    else:
        start = int( (size - scatter) * itr / max_iter )
        interval = ( min(start, size - max_len - 2) , min(start + scatter, size - max_len - 1))
    return random_chunks(n, None, None, max_len, interval)


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


def random_file_from_dump(dump_url):
    def get_lines(f, offset, length):
        status, chunk = f.read(offset=offset, size=length)
        if not status.ok or len(chunk) != length:
            raise RuntimeError(f"failed to read dump file {dump_url}: {status.code} {status.message}, length: {len(chunk)}")
        return chunk.decode('utf-8').split('\n')

    max_line_length = 50000
    with client.File() as f:
        status, data = f.open(dump_url)
        if not status.ok:
            raise RuntimeError(f"failed to open dump file {dump_url}: {status.code} {status.message}")
        status, stat = f.stat()

        if not status.ok:
            raise RuntimeError(f"failed to stat dump file {dump_url}: {status.code} {status.message}")

        size = stat.size
        if size < max_line_length:
            raise RuntimeError(f"Dump {dump_url} is too small")

        offset = randint(0, size - max_line_length)
        newlines_found = 0
        res = ''
        itr = 1000
        while newlines_found < 2 or itr <= 0:
            lines = get_lines(f, offset, max_line_length)
            llen = len(lines)
            if llen >=3:
                #Prefer 'prod' lines, but if there are none, select whatever is available
                res = lines[1]
                for l in lines[1:-1]:
                    if l.startswith('prod'):
                        res = l
                        break
            elif llen == 2:
                if newlines_found == 1:
                    res += lines[0]
                else:
                    res += lines[1]
            else:
                if newlines_found == 1:
                    res += lines[0]
            newlines_found += llen - 1
            offset += max_line_length
            itr -= 1
        if itr <= 0:
            res = None
        return res


def check_file(dump_url):
    res = False
    with client.File() as f:
        status, data = f.open(dump_url)
        if status.ok:
            status, stat = f.stat()
            if status.ok:
                size = stat.size
                if size >= 2*1000**3:
                    res = True
    return res


def do_readvs(file_url, scatter=128*1024*1024 + 1024*16, ntimes=2, nchunks=1024, max_len=1024, test_type='random', silent=False, sorted_chunks=True):
    #Dummy sum operation, to do some CPU work and prevent job from stalling
    dummy_sum = 0
    with client.File() as f:
        f.open(file_url)
        status, stat = f.stat()
        res = 0
        print("Open status:",  status, file_url)
        if not status.ok:
            raise ValueError(f"Failed to stat file {file_url}")
        size = stat.size
        for itr in range(ntimes):
            if test_type == 'random':
                chunks = random_chunks(nchunks, size, scatter, max_len)
            elif test_type == 'border':
                chunks = border_chunks(nchunks, size)
            elif test_type == 'lhcb_job':
                chunks = jobsim_chunks(nchunks, size, scatter, max_len, ntimes, itr=itr)
            else:
                raise ValueError("Wrong test type: {0}".format(test_type))

            if sorted_chunks:
                chunks = sorted(chunks, key=lambda x: x[0])

            status, response = f.vector_read(chunks=chunks)
            if not status.ok:
                print(f"Failed to readv file, status={status}, resp={response}, chunks={chunks if not silent else len(chunks)}")
                res = 1
            else:
                print(f"Readv finished successfully: {status}, min_offset={min(x[0] for x in chunks)}, max_offset={max(x[1] + x[0] for x in chunks)}", file=sys.stderr)
            dummy_sum += math.sqrt(itr) + math.sin(itr) + math.cos(itr)
    print("Sum=", dummy_sum)

    #jobsim_chunks.iter = 0
    return res



if __name__ == '__main__':
    args = parse_args()
    #parse_res = urlparse(url)
    #server = parse_res.scheme + '://' + parse_res.netloc
    #max_iov, max_ior = get_server_limits(server)
    #while True:
    res = 0
    for _ in range(args.nfiles):
        if args.url:
            url = args.url
        elif args.url_list:
            url = random_line(args.url_list)
        elif args.dump_url:
            for _ in range(1000):
                url = random_file_from_dump(args.dump_url)
                url = ''.join(args.dump_url.split(':accounting')[0] + ':' + url)
                if check_file(url):
                    break
                else:
                    url = None
        if url is None:
            url = args.dump_url
        tres = do_readvs(url, max_len=8192, test_type=args.test_type, silent=args.silent, ntimes=args.ntimes, scatter=args.scatter, sorted_chunks=args.chunks_sorted, nchunks=args.chunks_number)
        if tres == 1:
            res = 16
    sys.exit(res)
