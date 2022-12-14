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
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args() 
    data = pandas.read_csv(args.data)

    kwargs = {}
    if args.bins:
        kwargs['bins'] = args.bins
    if args.type == 'ecdf':
        plt = seaborn.displot(data, x='duration', kind='ecdf')
        plt.set(title='readv operations ECDF')
        plt.set_xlabels('duration, seconds')
    if args.type == 'histogram':
        plt = seaborn.displot(data, x='duration', hue='state', log_scale=(False, True), **kwargs)
        plt.set(title='readv operations')
        plt.set_xlabels('duration, seconds')
    elif args.type == 'bivalue':
        plt = seaborn.displot(data, x='duration', hue='state', y='chunks', **kwargs)
        plt.set_xlabels('duration, seconds')
    plt.savefig(args.output, dpi=args.resolution)
