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
    parser.add_argument('-n', '--normalize', help="Normalize bins, to show relative results", action='store_true')
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
    stats = {'gen': {}, 'host': {}}
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
        status = job['Status']
        res['status'].append(status)

        for key in stats.keys():
            val = res[key][-1]
            if val in stats[key]:
                if status in stats[key][val]:
                    stats[key][val][status] += 1
                else:
                    stats[key][val][status] = 1
            else:
                stats[key][val] = {status: 1}

    title='Number of jobs'
    ytitle = 'Count'
    if args.normalize:
        title='Jobs per ' + args.group
        ytitle = 'Fraction'
        norm_coeffs_dict = {}
        for gen, val in stats['gen'].items():
            norm_coeffs_dict[gen] = 1.0 / sum(x for x in val.values())
        norm_coeffs = []
        for gen in res['gen']:
            norm_coeffs.append(norm_coeffs_dict[gen])            

    data = pandas.DataFrame.from_dict(res)
    x_data = 'host' if args.group == 'WN' else 'gen'
    xticks = [i for i in range(len(WN_GENS))]
    if x_data == 'host':
        kwargs = {'binwidth': 1}
    else:
        x_data = 'gen'
        kwargs = {'multiple': 'stack'}
        if args.normalize:
            kwargs['weights'] =  norm_coeffs
            kwargs['bins'] = sum(1 for x in stats['gen'])
            kwargs['shrink'] = 0.8
            xticks = [i*0.83+0.42 for i in range(len(WN_GENS))]

    plt = seaborn.displot(data, x=x_data, hue='status', **kwargs) #, palette=["#00ff00", "#ff0000"])
    plt.set(title=title)
    plt.set_ylabels(ytitle)
    if args.group == 'WN':
        pyplot.xticks([x[0] for x in WN_GENS], [i[1] for i in WN_GENS], rotation=90)
    else:
        pyplot.xticks(xticks, [i[1] for i in WN_GENS], rotation=90)
    plt.savefig(args.output, dpi=args.resolution)
