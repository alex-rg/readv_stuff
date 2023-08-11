#!/usr/bin/env python3

import re
import sys
import pytz
import argparse
import datetime

from contextlib import contextmanager
from dateutil import parser as time_parser

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='file to parse')
    parser.add_argument('-t', '--tz', help='Specify timezone for times. Only use this if timezone info is not given in the log', default=None)
    return parser.parse_args()


@contextmanager
def open_stdin(_):
    yield sys.stdin


def parse_time(s, tz=False):
    t = time_parser.parse(  s + ( (' ' + tz) if tz is not None else '' )  )
    return int( t.timestamp() )


if __name__ == '__main__':
    args = parse_args()
    if args.file == '-':
        cm = open_stdin
    else:
        cm = open

    ts_parser = lambda x: parse_time(x, args.tz)
    found = {}
    times = []
    f_open_rexp = re.compile('^(.*) lcg[0-9]+.*File descriptor ([0-9]+) associated to file ([^ ]+) opened in read mode$')
    f_close_rexp = re.compile('^(?P<TS>.*) lcg[0-9]+.*XrdCephOssBufferedFile::Summary: \{"fd":(?P<fd>[0-9]+), "Elapsed_time_ms":(?P<elapsed_time>[0-9]+), "path":"(?P<path>[^"]+)", read_B:(?P<read_b>[0-9]+), readV_B:(?P<readv_b>[0-9]+), readAIO_B:(?P<readaio_b>[0-9]+), writeB:(?P<write_b>[0-9]+), writeAIO_B:(?P<writeaio_b>[0-9]+).*')
    with cm(args.file) as fd:
        for line in fd:
            m = f_open_rexp.match(line)
            if m:
                ts, fd, path = ts_parser(m.group(1)), int(m.group(2)), m.group(3)
                if (fd, path) in found:
                    raise ValueError("File {0} (fd {1}) was found twice".format(path, fd))
                found[(fd, path)] = ts

            m = f_close_rexp.match(line)
            if m:
                ts, fd, path = ts_parser(m.group('TS')), int(m.group('fd')), m.group('path')
                read_b, readv_b, readaio_b, write_b, writeaio_b = [int(m.group(x)) for x in ('read_b', 'readv_b', 'readaio_b', 'write_b', 'writeaio_b')]
                elapsed_time = int(m.group('elapsed_time'))
                try:
                    start = found[(fd, path)]
                except KeyError:
                    if read_b == 0 and readv_b == 0 and readaio_b == 0:
                        print("Open log message for file {0} (fd {1}) not found, though it looks like it is a write".format(path, fd), file=sys.stderr)
                    else:
                        print("Warning, open log message for file {0} (fd {1}) not found, will calculate ts from close message".format(path, fd), file=sys.stderr)
                        start = ts - elapsed_time // 1000
                times.append( (start, ts, fd, path) )
                try:
                    found.pop( (fd, path) )
                except KeyError:
                    pass

    for start, end, fd, path in times:
        print(start, end, fd, path)
