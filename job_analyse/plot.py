#!/usr/bin/env python3
import json
import argparse

import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('data', help="data file")
    parser.add_argument('-o', '--output', help="Put output in a file", default='./output.png')
    parser.add_argument('-d', '--dpi', help="Image resolution, dpi", default=300, type=int)
    parser.add_argument('-t', '--title', help="Plot title", default=None)
    parser.add_argument('-p', '--plot_type', help="Plot type", choices=['efficiency'], default='efficiency')
    parser.add_argument('-s', '--size', help="Picture size, in a form '<width>,<height>'", default=None)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    num = 0
    res = []
    with open(args.data) as fd:
        for line in fd:
            efficiency, item, all_jobs = line.split()
            res.append( (item, float(efficiency)) )
              

    if args.size:
        plt.figure(figsize=[int(x) for x in args.size.split(',')])
    if args.plot_type == 'efficiency':
        x = [k for k in range(len(res))]
        y = [v[1] for v in res]
        plt.bar(x, y)
    plt.xticks(x, [v[0] for v in res], rotation=90)
    if args.title is not None:
        plt.title(args.title)
    plt.savefig(args.output, dpi=args.dpi)
