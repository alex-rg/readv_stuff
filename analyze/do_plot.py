#!/usr/bin/env python

import pandas
import seaborn
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', help='Csv file to plot', required=True)
    parser.add_argument('-o', '--output', help='Plot output', default='./plot.png')
    parser.add_argument('-r', '--resolution', help='Resolution, in dpi', default=300, type=int)
    parser.add_argument('-b', '--bins', help='Number of bins for histogram', type=int)
    parser.add_argument('-t', '--type', help='Which plot to draw. Either histogram, ecdf or bivalue. Default is histogram', default='histogram')
    parser.add_argument('-w', '--what', help='What to plot. Either duration or chunks', default='duration')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args() 
    data = pandas.read_csv(args.data)

    kwargs = {}
    if args.bins:
        kwargs['bins'] = args.bins
    x_val = args.what
    if x_val == 'chunks':
        title = 'readv chunks'
        xtitle = 'Number of chunks'
    else:
        title = 'readv operations'
        xtitle = 'duration, seconds'
    if args.type == 'ecdf':
        plt = seaborn.displot(data, x=x_val, kind='ecdf')
        plt.set(title='readv operations ECDF')
        plt.set_xlabels(xtitle)
    if args.type == 'histogram':
        plt = seaborn.displot(data, x=x_val, hue='state', log_scale=(False, True), **kwargs)
        plt.set(title=title)
        plt.set_xlabels(xtitle)
    elif args.type == 'bivalue':
        plt = seaborn.displot(data, x='duration', hue='state', y='chunks', **kwargs)
        plt.set_xlabels('duration, seconds')
    plt.savefig(args.output, dpi=args.resolution)
