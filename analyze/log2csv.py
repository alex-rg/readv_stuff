#!/usr/bin/env python3
import datetime
import argparse
import sys
import re

from contextlib import contextmanager


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('log', help='Path to log file that should be analized')
    parser.add_argument('-o', '--output', help='Path to the output file', default='./readv_times.csv')
    return parser.parse_args()


def timestamp2epoch(stamp):
    res = datetime.datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S.%f %z')
    res = (res - datetime.datetime(1970, 1, 1, tzinfo=res.tzinfo)).total_seconds()
    return res


@contextmanager
def open_stdout():
    yield sys.stdout


def log2csv(log_path, csv_path):
    def _extract_key(match):
        time = timestamp2epoch(match.group('time'))
        size = match.group('size')
        chunks = match.group('chunks')
        key = (size, chunks)
        return (key, time)

    readvs = {}
    if csv_path == '-':
        opener = open_stdout
    else:
        opener = lambda: open(path, 'w')

    with opener() as csv_fd:
        with open(log_path) as log_fd:
            timestamp_rexp = r'^\[(?P<time>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:\.]+ \+[0-9]+)\]'
            readv_data_rexp = r'\(handle: [0-9a-fx]+, chunks: (?P<chunks>[0-9]+), total size: (?P<size>[0-9]+)\)'
            readv_send_rexp = r'Message kXR_readv {0} has been successfully sent'.format(readv_data_rexp)
            readv_end_rexp = r'Got a kXR_(?P<state>ok|error) response to request kXR_readv {0}'.format(readv_data_rexp)

            start_rexp = re.compile(r'{0}.*{1}'.format(timestamp_rexp, readv_send_rexp))
            end_rexp = re.compile(r'{0}.*{1}'.format(timestamp_rexp, readv_end_rexp))
            for line in log_fd:
                m = start_rexp.match(line)
                if m:
                    key, start = _extract_key(m)
                    try:
                        readvs[key].append(start)
                    except KeyError:
                        readvs[key] = [start]

                m = end_rexp.match(line)
                if m:
                    key, end = _extract_key(m)
                    res = 0 if m.group('state') == 'ok' else 1
                    try:
                        start = readvs[key].pop()
                    except KeyError:
                        print("Found end of readv {0}, but can not find start! Probably log is incomplete".format(key))
                    else:
                        print('{0},{1},{2},{3},{4}'.format(start, end - start, res, key[0],key[1]), file=csv_fd)


if __name__ == '__main__':
    args = parse_arguments()
    log2csv(args.log, args.output)
