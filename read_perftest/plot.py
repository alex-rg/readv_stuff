#!/usr/bin/env python3
import re
import json
import argparse

import statistics
import matplotlib.pyplot as plt


colors = ['b', 'g', 'c', 'm', 'y', 'k']

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('data', help="data file")
    parser.add_argument('-o', '--output', help="Put output in a file", default='./output.png')
    parser.add_argument('-d', '--dpi', help="Image resolution, dpi", default=300, type=int)
    parser.add_argument('-t', '--title', help="Plot title", default=None)
    parser.add_argument('-p', '--plot_type', help="Plot type", choices=['speed', 'errors'], default='speed')
    parser.add_argument('-P', '--speed_point', help="What points to plot for speed", choices=['average', 'median'], default='speed')
    parser.add_argument('-n', '--nbunch', help="Number of bunches", default=10, type=int)
    parser.add_argument('-s', '--speed', help="Max WN speed in bytes. If given, a 'theoretical' speed will be plotted also", default=None, type=int)
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
                if tres:
                    if jobs in res:
                        res[jobs].append( tres )
                    else:
                        res[jobs] = [ tres ]
                jobs = int(m.group(1))
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
                    if ecode != 0:
                        continue
                    speed = 10**9 / time
                    m = min(m, speed)
                    M = max(M, speed)
                    avg += speed
                    n += 1
                if avg == 0:
                    continue
                avg = avg / n
                med = statistics.median( 10**9 / x[0] for x in bunch)
                if args.speed_point == 'average':
                    point = avg
                elif args.speed_point == 'median':
                    point = med
                else:
                    raise ValueError(f"Incorrect value for {args.speed_point}")
                plt.errorbar([k + i * 0.03], [point], [[max(point-m, 0)], [max(M-point, 0)]], fmt='o' + colors[i % len(colors)], capsize=6, linewidth=2)
        if args.speed is not None:
            t = [4*i for i in range(1, 33)]
            plt.plot([k for k in t], [args.speed/k for k in t], linewidth=2)
            plt.legend([f'{args.speed/(1000*1000)} MB/s'])
        plt.xlabel('Transfers')
        plt.ylabel('Speed, Bytes/s')
    elif args.plot_type == 'errors':
        x = [k for k in res]
        success = [ sum(sum(t[1] == 0 for t in arr ) for arr in res[_k]) for _k in x ]
        errors = [ sum(sum(t[1] != 0 for t in arr ) for arr in res[_k]) for _k in x ]
        plt.bar(x, errors, color='r')
        plt.bar(x, success, color='b', bottom=errors)
        plt.legend(['error', 'success'])
    plt.xticks([int(_x) for _x in res], rotation=90)
    if args.title is not None:
        plt.title(args.title)
    plt.savefig(args.output, dpi=args.dpi)
