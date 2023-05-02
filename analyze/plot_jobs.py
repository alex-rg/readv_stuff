#!/usr/bin/env python

import re
import sys
import json
import pandas
import seaborn
import argparse

from matplotlib import pyplot

WN_GENS = [ (2270, '2017-dell'), (2326, '2017-xma'), (2386, '2018-xma'), (2434, '2019-dell'), (2537, '2020-xma'), (2642, '2021-xma')]

def get_gen(wn):
    idx = 0
    for border, _ in WN_GENS:
        if wn <= border:
            break
        idx += 1
    return idx


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--group', help='How to group bins. Either WN or GEN', choices=['WN', 'GEN'], default='WN')
    parser.add_argument('-o', '--output', help='Path to the output file', required=True)
    parser.add_argument('-r', '--resolution', help="Plot's resolution", default=300, type=int)
    parser.add_argument('file', help='File(s) to process')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()

    if args.file == '-':
        data = sys.stdin.read()
    else:
        with open(args.file) as fd:
            data = fd.read()
    data = json.loads(data)
     
    res = {'ID': [], 'status': [], 'host': [], 'gen': []}
    for job in data:
        res['ID'] = job['JobID']
        m = re.match('.*lcg([0-9]+).*', job['HostName'])
        if m:
            host_num = int(m.group(1))
            res['host'].append(host_num)
            res['gen'].append(get_gen(host_num))
        else:
            res['host'].append(-1)
            res['gen'].append(-1)
        res['status'].append(job['Status'])
    data = pandas.DataFrame.from_dict(res)
    x_data = 'host' if args.group == 'WN' else 'gen'
    if x_data == 'host':
        x_data = 'host' if args.group == 'WN' else 'gen'
        kwargs = {'binwidth': 1}
    else:
        x_data = 'gen'
        kwargs = {'stat': 'probability', 'multiple': 'stack', 'common_norm': False}
    plt = seaborn.displot(data, x=x_data, hue='status', **kwargs) #, palette=["#00ff00", "#ff0000"])
    plt.set(title='Number of jobs')
    if args.group == 'WN':
        pyplot.xticks([x[0] for x in WN_GENS], [i[1] for i in WN_GENS], rotation=90)
    else:
        pyplot.xticks([i for i in range(len(WN_GENS))], [i[1] for i in WN_GENS])
    plt.savefig(args.output, dpi=args.resolution)
    #data = pandas.read_csv(args.data)

#    if args.type == 'ecdf':
#        plt = seaborn.displot(data, x=x_val, kind='ecdf')
#        plt.set(title='readv operations ECDF')
#        plt.set_xlabels(xtitle)
#    if args.type == 'histogram':
#        plt = seaborn.displot(data, x=x_val, hue='state', log_scale=(False, True), **kwargs)
#        plt.set(title=title)
#        plt.set_xlabels(xtitle)
#    elif args.type == 'bivalue':
#        plt = seaborn.displot(data, x=x_val, y='chunks', **kwargs)
#        plt.set_xlabels('scatter, bytes')

