#!/usr/bin/env python3
import argparse
import sys
import re

def do_print(res, rexp=None):
    max_name_len = 1
    for fds in res:
        for k, v in fds.items():
            if rexp is None or re.match(rexp, v['filename']):
                if len(v['filename']) > max_name_len:
                    max_name_len = len(v['filename'])
    format_string = '{{0:{0}}} {{1:10}} {{2:10}} {{3:10.2f}} {{4:15}}'.format(max_name_len + 5)
    for fds in res:
        for fd, stats in fds.items():
            if rexp is None or re.match(rexp, stats['filename']):
                print(format_string.format(stats['filename'], stats['ceph_count'], stats['read_count'], (1 - stats['ceph_count']/stats['read_count']) * 100, stats['bytes_read']))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rexp', help="Only select filename(s) that matches this regexp (python regexp)", default=None)
    return parser.parse_args()


if __name__ == '__main__':
    res = []
    fds = {}
    last_fd = -1
    fd = last_fd
    args = parse_args()
    for line in sys.stdin:
        m = re.match('.*ceph_close: closed fd ([0-9]+) for file ([^ ]*), read ops count ([0-9]+),.*', line)
        if m:
            fd = int(m.group(1))
            if fd < last_fd:
                res.append(fds)
                fds = {}
            filename = m.group(2)
            read_count = int(m.group(3))
            fds[fd] = { 'read_count': read_count, 'ceph_count': 0, 'filename': filename, 'bytes_read': 0 }
            last_fd = fd

        m = re.match('.*. CephIOAdapterRaw::Summary fd:([0-9]+).*nread:([0-9]+).*bytesread:([0-9]+)', line)
        if m:
            fd = int(m.group(1))
            read_count = int(m.group(2))
            fds[fd]['ceph_count'] += read_count
            fds[fd]['bytes_read'] += int(m.group(3))

    do_print(res, rexp=args.rexp)
