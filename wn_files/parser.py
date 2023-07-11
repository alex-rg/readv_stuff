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
    f_close_rexp = re.compile('^(.*) lcg[0-9]+.*XrdCephOssBufferedFile::Summary: \{"fd":([0-9]+).*, "path":"([^"]+)",.*')
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
                ts, fd, path = ts_parser(m.group(1)), int(m.group(2)), m.group(3)
                try:
                    start = found[(fd, path)]
                except KeyError:
                    print("Warning, open log message for file {0} (fd {1}) not found, skipping".format(path, fd), file=sys.stderr)
                else:
                    times.append( (start, ts, fd, path) )
                    found.pop( (fd, path) )
    for start, end, fd, path in times:
        print(start, end, fd, path)
