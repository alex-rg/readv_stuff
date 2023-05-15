#!/usr/bin/env python3
import sys
import re


def do_print(fds):
    for fd, stats in fds.items():
        print(fd, stats['filename'], stats['ceph_count'], stats['read_count'], "{0:.3}%".format(stats['ceph_count']/stats['read_count'] * 100))


if __name__ == '__main__':
    fds = {}
    last_fd = -1
    fd = last_fd
    for line in sys.stdin:
        m = re.match('.*ceph_close: closed fd ([0-9]+) for file ([^ ]*), read ops count ([0-9]+),.*', line)
        if m:
          if fd < last_fd:
              do_print(fds)
              fds = {}
          fd = int(m.group(1))
          filename = m.group(2)
          read_count = int(m.group(3))
          fds[fd] = { 'read_count': read_count, 'ceph_count': 0, 'filename': filename }
          last_fd = fd

        m = re.match('.*. CephIOAdapterRaw::Summary fd:([0-9]+).*nread:([0-9]+).*', line)
        if m:
            fd = int(m.group(1))
            read_count = int(m.group(2))
            fds[fd]['ceph_count'] += read_count

    do_print(fds)

