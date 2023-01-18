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
    parser.add_argument('-r', '--request_type', help='Type of the the request that should be extracted. Default is readv.', default='readv')
    return parser.parse_args()


def timestamp2epoch(stamp):
    res = datetime.datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S.%f %z')
    res = (res - datetime.datetime(1970, 1, 1, tzinfo=res.tzinfo)).total_seconds()
    return res


@contextmanager
def open_stdout():
    yield sys.stdout


@contextmanager
def open_stdin():
    yield sys.stdin


def log2csv(log_path, csv_path, req_type='readv'):
    def _extract_key(match):
        time = timestamp2epoch(match.group('time'))
        if req_type == 'readv':
            size = match.group('size')
            chunks = match.group('chunks')
            if chunks.endswith(']'):
                chunks = len(chunks.split(';')) -1
            key = (size, chunks)
        elif req_type == 'read':
            size = match.group('size')
            offset = match.group('offset')
            key = (size, offset)
        return (key, time)

    requests = {}
    if csv_path == '-':
        opener = open_stdout
    else:
        opener = lambda: open(csv_path, 'w')

    if log_path == '-':
        input_opener = open_stdin
    else:
        input_opener = lambda: open(log_path)

    with opener() as csv_fd:
        with input_opener() as log_fd:
            timestamp_rexp = r'^\[(?P<time>[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:\.]+ \+[0-9]+)\]'
            if req_type == 'readv':
                req_data_rexp = r'\(handle: [0-9a-fx]+, chunks: (?P<chunks>[0-9 ,\[\]:;ofsetiz()]+), total size: (?P<size>[0-9]+)\)'
                req_send_rexp = r'Message kXR_readv {0} has been successfully sent'.format(req_data_rexp)
                req_end_rexp = r'(?:Got a kXR_(?P<state>ok|error) response to request|Handling error while processing) kXR_readv {0}'.format(req_data_rexp)
            elif req_type == 'read':
                req_data_rexp = r'\(handle: [0-9a-fx]+, offset: (?P<offset>[0-9]+), size: (?P<size>[0-9]+)\)'
                req_send_rexp = r'Message kXR_read {0} has been successfully sent'.format(req_data_rexp)
                req_end_rexp = r'(?:Got a kXR_(?P<state>ok|error) response to request|Handling error while processing) kXR_read {0}'.format(req_data_rexp)
            else:
                raise ValueError("Unsupported request type {0}: expected read or readv".format(req_type))

            start_rexp = re.compile(r'{0}.*{1}'.format(timestamp_rexp, req_send_rexp))
            end_rexp = re.compile(r'{0}.*{1}'.format(timestamp_rexp, req_end_rexp))

            chunk_rexp = re.compile(r'.*read buffer for chunk ([0-9@]+)$')

            lines_written = 0

            max_spread = 0
            biggest_spread_request = 'none'
            best_buf_start, best_buf_end = -1, -1
            for line in log_fd:
                m = start_rexp.match(line)
                if m:
                    buf_start, buf_end = 10**100, -1
                    key, start = _extract_key(m)
                    try:
                        requests[key].append(start)
                    except KeyError:
                        requests[key] = [start]

                if req_type == 'readv':
                    m = chunk_rexp.match(line)
                    if m:
                        size, pos = [int(x) for x in m.group(1).strip().split('@')]
                        if size + pos > buf_end:
                            buf_end = size + pos
                        if pos < buf_start:
                            buf_start = pos
                        #print("bs={0}, be={1}".format(buf_start, buf_end), file=sys.stderr)


                m = end_rexp.match(line)
                if m:
                    key, end = _extract_key(m)
                    if req_type == 'readv':
                        if max_spread < buf_end - buf_start:
                            max_spread = buf_end - buf_start
                            best_buf_start, best_buf_end = buf_start, buf_end
                            biggest_spread_request = key
                    res = 0 if m.group('state') == 'ok' else 1
                    try:
                        start = requests[key].pop()
                    except (KeyError, IndexError):
                        print("Found end of request {0}, but can not find start! Probably log is incomplete, multiple error messages are present.".format(key), file=sys.stderr)
                    else:
                        lines_written += 1
                        if req_type == 'readv':
                            print('{0},{1},{2},{3},{4},{5}'.format(start, end - start, res, key[0],key[1], buf_end - buf_start), file=csv_fd)
                        else:
                            print('{0},{1},{2},{3},{4}'.format(start, end - start, res, key[0],key[1]), file=csv_fd)
                        if (lines_written + 1) % 5 == 0:
                            csv_fd.flush()
            print("Max spread = {0}, request = {1}, buf_start={2}, buf_end={3}".format(max_spread, key, best_buf_start, best_buf_end), file=sys.stderr)


if __name__ == '__main__':
    args = parse_arguments()
    log2csv(args.log, args.output, req_type=args.request_type)
