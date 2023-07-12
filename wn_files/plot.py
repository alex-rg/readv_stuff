#!/usr/bin/env python3

import sys
import argparse

from parser import open_stdin
from matplotlib import pyplot as plt
from time import strftime, localtime


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='file to parse')
    parser.add_argument('-p', '--plot_type', help='plot type', choices=['simple', 'count'])
    parser.add_argument('-o', '--output', help='Output file', default='plot.png')
    parser.add_argument('-H', '--height', help='Picture`s height', type=int, default=None)
    parser.add_argument('-w', '--width', help='Picture`s width', type=int, default=None)
    parser.add_argument('-t', '--title', help='Picture`s title', default=None)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.file == '-':
        cm = open_stdin
    else:
        cm = open

    res = []
    with cm(args.file) as fd:
        for line in fd:
            ts1, ts2, fd, path = line.strip().split(' ')
            ts1, ts2 = (int(x) for x in (ts1, ts2))
            res.append( (ts1, ts2) )

    fig = plt.figure()
    if args.width:
        fig.set_figwidth(args.width)
    if args.height:
        fig.set_figheight(args.height)

    if args.plot_type == 'simple':
        plt.figure().set_figheight(15)
        idx = 0
        for start, end in res:
            plt.plot( [start, end], [idx, idx], '-b')
            idx += 1
    else:
        #res = [(2, 3), (1, 4), (1, 10), (2, 12)]
        res.sort()
        x_vals = []
        y_vals = []
        data = {}
        arr = [(x[0], 's') for x in res] + [(x[1], 'e') for x in res]
        arr.sort(key=lambda x: x[0])
        o_files = 0
        for val, typ in arr:
            if typ == 's':
                o_files += 1
            elif typ == 'e':
                o_files -= 1
            if x_vals and x_vals[-1] == val:
                y_vals[-1] = o_files
            else:
                x_vals.append(val)
                y_vals.append(o_files)
            
        print(x_vals)
        print(y_vals)
        plt.step(x_vals, y_vals, where="post")
        plt.ylabel('nofiles')
        plt.ylim(bottom=0)
        plt.xlim(min(x_vals), max(x_vals))
    if args.title:
        plt.title(args.title)
    xticks = plt.xticks()
    plt.xticks(xticks[0], labels=[strftime('%d.%m %H:%M', localtime(x)) for x in xticks[0]], rotation=90)
    plt.savefig(args.output, dpi=300)
