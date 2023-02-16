#!/bin/bash

source /cvmfs/lhcb.cern.ch/group_login.sh
export X509_USER_PROXY=/lhcb_job/proxy.pem
export XRD_LOGLEVEL=Dump
#mkfifo ./stderr_fifo
#cat ./stderr_fifo | tee >( ../../../analyze/log2csv.py -o ./vector_times.csv -) >(../../../analyze/log2csv.py -o ./read_times.csv -r read - ) | tail -n 10000 > last_std.err &
lb-run --siteroot=/cvmfs/lhcb.cern.ch/lib -c x86_64_v2-centos7-gcc11-opt --path-to-project /lhcb_job/DaVinciDev_46.4 gaudirun.py script.py data.py 2> std.err
#retcode="$?"
#[ "$retcode" -eq 0 ] && rm ./stderr_fifo || exit "$retcode"
