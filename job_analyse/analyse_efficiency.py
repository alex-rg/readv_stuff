#!/usr/bin/env python3
import re
import sys
import json
import argparse

from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-b", "--boundaries", help="Print efficiencies for nodes with numbers from <a> to <b> inclusive, where '<a>,<b>' is the value", default=None)
    g.add_argument("-n", "--node", help="Print individual job efficiencies for particular node(s). Multiple nodes shoud be comma-separated", default=None)
    g1 = parser.add_mutually_exclusive_group()
    g1.add_argument("-s", "--strict", help="Strict mode. For failed jobs cputime is set to 0.", action='store_true')
    g1.add_argument("-l", "--loose", help="Loose mode. Only consider successfull jobs.", action='store_true')
    parser.add_argument("-m", "--merge", help="Merge all hosts into a single group.", action='store_true')
    parser.add_argument("-S", "--since", help="Only consider jobs finished after <DD>-<MM>-<YYYY>T<HH>:<MM>.", default=None)
    parser.add_argument("-U", "--until", help="Only consider jobs finished before <DD>-<MM>-<YYYY>T<HH>:<MM>.", default=None)
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

    start_ts = int(datetime.strptime(args.since, '%d-%m-%YT%H:%M').strftime("%s")) if args.since else None
    end_ts = int(datetime.strptime(args.until, '%d-%m-%YT%H:%M').strftime("%s")) if args.until else None

    for job in data:
        try:
            cputime = float(job['TotalCPUTime(s)'])
            walltime = job['WallClockTime(s)']
            host_str = job['HostName']
            status = job['Status']
        except KeyError:
            continue
        if start_ts or end_ts:
            try:
                job_ts = job['timestamp']
            except KeyError:
                continue
            job_ts = job_ts / 1000
            if (start_ts and start_ts > job_ts) or (end_ts and end_ts < job_ts):
                continue

        if args.loose and status != 'Done':
            continue
        m = host_rexp.match(job['HostName'])
        if m:
            host = m.group(1)
            num = int(m.group(2))
        else:
            continue

        failed = 0
        if status == 'Failed':
            failed = 1
            if args.strict:
                cputime = 0

        #Process individual jobs, do not save anything
        if nodes and host in nodes:
            print(job['JobID'], host, cputime / walltime) 
        #Process nodes
        else:
            if num >= bot_border and num <= up_border:
               if args.merge:
                   key = 'all' if args.boundaries is None else args.boundaries
               else:
                   key = host
               if key in res:
                   res[key]['CPUTime'] += cputime
                   res[key]['WALLTime'] += walltime
                   res[key]['cnt'] += 1
                   res[key]['failed'] += failed
               else:
                   res[key] = {'CPUTime': cputime, 'WALLTime': walltime, 'cnt': 1, 'failed': failed}
 
    if not nodes:
        for key, res in res.items():
            print(res['CPUTime'] / res['WALLTime'], key, res['cnt'], res['failed'])
