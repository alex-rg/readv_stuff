#!/usr/bin/env python
import argparse

import matplotlib.pyplot as plt
import sys

from matplotlib.collections import LineCollection

DEF_OUTPUT='./plot.png'

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', help="File(s) to process, comma-separated", required=True)
    parser.add_argument('-o', '--output', help="Output picture. Default={0}".format(DEF_OUTPUT), default=DEF_OUTPUT)
    parser.add_argument('-f', '--fake_time', help="Do not use actual timestamps, use request's number instead.", action='store_true')
    parser.add_argument('-r', '--read_length', help="If given, it is assumed that all reads have this length. Usefull for plotting small reads. File with read's data is assumed to be the first one.", type=int, default=None)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    files = args.data.split(',')
    data = []
    idx = 0 
    for fname in files:
        with open(fname) as fd:
            for line in fd:
               time, _, _, _, _, length, offset  = line.split(',')
               time, length, offset = float(time), int(length), int(offset)
               data.append( (time, length, offset, idx) )
        idx = idx + 1

    data = sorted(data, key=lambda x: x[0])

    X = []
    Y = []
    res = []
    colors = []
    lw = []

    my = 10**10
    My = -1
    mx, Mx = my, My

    fig, ax = plt.subplots()
    cnt = 0
    for time, length, offset, idx in data:
        if args.fake_time:
            y_val = cnt
        else:
            y_val = time
        mx = min(mx, offset)
        Mx = max(Mx, offset + length)
        my = min(my, y_val)
        My = max(My, y_val)
        if idx == 0 and args.read_length:
            length = args.read_length
        res.append(
            [
              [offset, y_val],
              [offset + length, y_val]
            ]
          )
        if idx == 0:
            colors.append('r')
            lw.append(0.2)
        else:
            lw.append(0.3)
            colors.append('b')
        cnt = cnt + 1
    lc = LineCollection(res, linewidth=lw, colors=colors)
    ax.add_collection(lc)
    ax.set_xlim(-1, Mx)
    ax.set_ylim(my, My)
    plt.savefig(args.output, dpi=1800.0)
