#!/usr/bin/env python3
import re
import json
import argparse

import matplotlib.pyplot as plt


colors = ['b', 'g', 'c', 'm', 'y', 'k']

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('data', help="data file")
    parser.add_argument('-o', '--output', help="Put output in a file", default='./output.png')
    parser.add_argument('-d', '--dpi', help="Image resolution, dpi", default=300, type=int)
    parser.add_argument('-t', '--title', help="Plot title", default=None)
    parser.add_argument('-p', '--plot_type', help="Plot type", choices=['speed', 'errors'], default='speed')
    parser.add_argument('-n', '--nbunch', help="Number of bunches", default=10, type=int)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    jobs = -1
    res = {}
    tres = []
    with open(args.data) as fd:
        for line in fd:
            m = re.match('^JOBS ([0-9]+)$', line)
            if m:
                jobs = int(m.group(1))
                if tres:
                    if jobs in res:
                        res[jobs].append( tres )
                    else:
                        res[jobs] = [ tres ]
                tres = []

            m = re.match('^([0-9]+) ([0-9]+)$', line)
            if m:
                time = int(m.group(1))
                estat = int(m.group(2))
                tres.append( (time, estat) )

    #print(json.dumps(res, indent=2))
    if args.plot_type == 'speed':
        for k in res:
            for i, bunch in enumerate(res[k]):
                M, m = -1, 10**10
                avg = 0
                n = 0
                for time, ecode in bunch:
                    speed = 10**9 / time
                    m = min(m, speed)
                    M = max(M, speed)
                    avg += speed
                    n += 1
                avg = avg / n
                plt.errorbar([k + i * 0.03], [avg], [[avg-m], [M-avg]], fmt='o' + colors[i % len(colors)], capsize=6, linewidth=2)
        plt.xlabel('Transfers')
        plt.ylabel('Speed, Bytes/s')
    elif args.plot_type == 'errors':
        x = [k for k in res]
        success = [ sum(sum(t[1] == 0 for t in arr ) for arr in res[_k]) for _k in x ]
        errors = [ sum(sum(t[1] != 0 for t in arr ) for arr in res[_k]) for _k in x ]
        plt.bar(x, success, color='b')
        plt.bar(x, errors, color='r')
        plt.legend(['success', 'error'])
    plt.xticks([int(_x) for _x in res])
    if args.title is not None:
        plt.title(args.title)
    plt.savefig(args.output, dpi=args.dpi)
