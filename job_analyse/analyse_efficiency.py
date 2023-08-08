#!/usr/bin/env python3
import re
import sys
import json
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-b", "--boundaries", help="Print efficiencies for nodes with numbers from <a> to <b> inclusive, where '<a>,<b>' is the value", default=None)
    g.add_argument("-n", "--node", help="Print individual job efficiencies for particular node(s). Multiple nodes shoud be comma-separated", default=None)
    parser.add_argument("-s", "--strict", help="Strict mode. For failed jobs cputime is set to 0.", action='store_true')
    parser.add_argument("file", help="File to parse")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.file == '-':
        data = json.loads(sys.stdin.read())
    else:
        with open(args.file) as fd:
            data = json.loads(fd.read())
    if args.boundaries:
        bot_border, up_border = (int (x) for x in args.boundaries.split(','))
    else:
        bot_border, up_border = -1, 10**10

    res = {}
    if args.node:
        nodes = args.node.split(',')
    else:
        nodes = None
    host_rexp = re.compile('.*(lcg([0-9]+))\.gridpp.rl.ac.uk$')
    for job in data:
        try:
            cputime = float(job['TotalCPUTime(s)'])
            walltime = job['WallClockTime(s)']
            host_str = job['HostName']
            status = job['Status']
        except KeyError:
            continue
        m = host_rexp.match(job['HostName'])
        if m:
            host = m.group(1)
            num = int(m.group(2))
        else:
            continue

        if args.strict:
            if status == 'Failed':
                cputime = 0

        #Process individual jobs, do not save anything
        if nodes and host in nodes:
            print(job['JobID'], host, cputime / walltime) 
        #Process nodes
        else:
            if num >= bot_border and num <= up_border:
               if host in res:
                   res[host]['CPUTime'] += cputime
                   res[host]['WALLTime'] += walltime
                   res[host]['cnt'] += 1
               else:
                   res[host] = {'CPUTime': cputime, 'WALLTime': walltime, 'cnt': 1}
 
    if not nodes:
        for key, res in res.items():
            print(res['CPUTime'] / res['WALLTime'], key, res['cnt'])
