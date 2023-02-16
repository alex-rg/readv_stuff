#!/usr/bin/env python3

import sys
import json
import argparse

from ast import literal_eval
from contextlib import contextmanager

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prod_conf', help="original prod conf file", required=False)
    parser.add_argument('-l', '--lfn_prefix', help="Prefix that converts lfn to pfn when added to the lfn", default="root://xrootd.echo.stfc.ac.uk:1095/lhcb:prod")
    parser.add_argument('-j', '--jdl', help="JDL that should be used to create new prodconf", required=True)
    parser.add_argument('-o', '--output_file', help="Where to put output. - sign for stdout. Default is stdout.", default="-")
    parser.add_argument('-s', '--summary_filename', help="Override summary file name.", default=None)
    parser.add_argument('-t', '--type', help="Job type. Either 'prod' or 'user'.", choices=['prod', 'user'], default='prod')
    args = parser.parse_args()
    return args

@contextmanager
def open_stdout():
    yield sys.stdout

if __name__ == '__main__':
    args = parse_args()
    if args.output_file == '-':
        opener = open_stdout
    else:
        opener = lambda : open(args.output_file, 'w')
    with opener() as fd:
        with open(args.jdl) as jdl_fd:
           input_data = literal_eval(jdl_fd.read())['InputData']
           input_data = [args.lfn_prefix + x for x in input_data]
           if args.type == 'prod':
                with open(args.prod_conf) as prod_conf_fd:
                    output = json.loads(prod_conf_fd.read())
                    output['input']['files'] = input_data
                    if args.summary_filename:
                        output['input']['xml_summary_file'] = args.summary_filename
                    fd.write(json.dumps(output, indent=2))
           elif args.type == 'user':
               fd.write("""#-- GAUDI jobOptions generated on Thu Jan 26 04:36:09 2023

from Gaudi.Configuration import *
from GaudiConf import IOHelper
IOHelper().inputFiles({0}, clear=True)

FileCatalog().Catalogs += [ 'xmlcatalog_file:pool_xml_catalog.xml' ]
""".format('[' + ',\n'.join("'" + x + "'" for x in input_data) + ']')
                        )
