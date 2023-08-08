#!/usr/bin/env python

import re
import sys
import json
import argparse
import datetime

TERMINAL_STATES = ['Done', 'Failed', 'Rescheduled', 'Completed']


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--select', help="Comma-separated list of jobIDs.", default=None)
    parser.add_argument('-t', '--type', help="What files to merge.", choices=['attributes', 'parameters', 'all'], default='attributes')
    parser.add_argument('files', help="Path to file(s) to merge.", nargs='+')
    return parser.parse_args()


def parse_data(filename, dtype='attrs'):
    res = []
    data_str = ''
    if dtype == 'attrs':
        rexp = '^=+$'
        parser = lambda x: eval(x)
    elif dtype == 'params':
        rexp = '^\{[0-9]+: \{.*$'
        parser = lambda x: [t for t in eval(x).values()][0]
    else:
        raise ValueError("Unexpected value for dtype: {0}".format(dtype))

    with open(filename) as fd:
        for line in fd:
            if re.match(rexp, line):
                if data_str:
                    try:
                        res.append( parser(data_str) )
                    except IndentationError:
                        print("Failed to parse:\n{0}".format(data_str))
                        sys.exit(1)
                if dtype == 'attrs':
                    data_str = ''
                    fd.readline()
                else:
                    data_str = line
            else:
                data_str += line
    res.append( parser(data_str) )
    return res


def merge(data, select_IDs=None):
    IDs = []
    res = []
    for d in data:
        for job in d:
            try:
                if job['JobID'] not in IDs and (select_IDs is None or job['JobID'] in select_IDs):
                    if job['Status'] in TERMINAL_STATES:
                        res.append(job)
                        IDs.append(job['JobID'])
            except KeyError:
                pass
    return res


def merge_attrs_and_params(attrs, params):
    for jdata in params:
        for jdata1 in attrs:
            if jdata1['JobID'] == jdata['JobID']:
                  for key in ('ApplicationStatus', 'Owner'):
                      jdata[key] = jdata1[key]
                  break


if __name__ == '__main__':
    args = parse_args()
    if args.type == 'attributes':
        dtype = 'attrs'
    elif args.type == 'parameters':
        dtype = 'params'
    elif args.type == 'all':
        dtype = 'all'
    else:
        raise ValueError("Unknown type {0}".format(args.type))

    select_IDs = None if args.select is None else [ int(x) for x in args.select.split(',') if x ]
    if dtype != 'all':
        data = []
        for filename in args.files:
            data.append(parse_data(filename, dtype=dtype))

        data = merge(data, select_IDs)
    else:
        data_attr = []
        data_parms = []
        for idx, filename in enumerate(args.files):
            if idx % 2 == 0:
                data_attr.append(parse_data(filename, dtype='attrs'))
            else:
                data_parms.append(parse_data(filename, dtype='params'))

        data_attr = merge(data_attr, select_IDs)
        data_parms = merge(data_parms, select_IDs)
        merge_attrs_and_params(data_attr, data_parms)
        data = data_parms

    print(json.dumps(data, indent=2, default=str))

